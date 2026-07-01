"""Validate curated McMaster catalog consistency (offline, no live scrape)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from backend.services.mcmaster_catalog import (
    CATALOG_PATH,
    M3_SOCKET_HEAD_BY_LENGTH_MM,
    normalize_catalog_key,
)

_TITLE_LENGTH_MM = re.compile(
    r"\bM\s*(\d+(?:\.\d+)?)\s*[×x]\s*(\d+(?:\.\d+)?)\s*mm\b",
    re.I,
)
_KEY_LENGTH_MM = re.compile(
    r"\bm\s*(\d+(?:\.\d+)?)\s*[-x×]\s*(\d+(?:\.\d+)?)\b",
    re.I,
)


@dataclass(frozen=True)
class CatalogIntegrityIssue:
    part_number: str
    code: str
    message: str


def _load_entries() -> list[dict]:
    if not CATALOG_PATH.is_file():
        return []
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return list(raw.get("entries", []))


def _title_metric_length(title: str) -> int | None:
    match = _TITLE_LENGTH_MM.search(title)
    if not match:
        return None
    return int(float(match.group(2)))


def _key_metric_length(key: str) -> int | None:
    normalized = normalize_catalog_key(key)
    match = _KEY_LENGTH_MM.search(normalized)
    if not match:
        return None
    return int(float(match.group(2)))


def check_catalog_integrity() -> list[CatalogIntegrityIssue]:
    """Return issues when catalog keys, titles, and rule tables disagree."""
    issues: list[CatalogIntegrityIssue] = []
    part_numbers_in_catalog = {e.get("part_number", "") for e in _load_entries()}

    for entry in _load_entries():
        part_number = entry.get("part_number", "")
        title = entry.get("title", "")
        title_length = _title_metric_length(title)

        for key in entry.get("keys", []):
            key_length = _key_metric_length(key)
            if title_length is not None and key_length is not None:
                if title_length != key_length:
                    issues.append(
                        CatalogIntegrityIssue(
                            part_number=part_number,
                            code="title_key_length_mismatch",
                            message=(
                                f"key {key!r} implies {key_length} mm but title "
                                f"implies {title_length} mm ({title!r})"
                            ),
                        )
                    )

    for length_mm, part_number in M3_SOCKET_HEAD_BY_LENGTH_MM.items():
        if part_number not in part_numbers_in_catalog:
            issues.append(
                CatalogIntegrityIssue(
                    part_number=part_number,
                    code="rule_missing_catalog_entry",
                    message=f"M3_SOCKET_HEAD_BY_LENGTH_MM[{length_mm}]={part_number} not in catalog JSON",
                )
            )
            continue
        entry = next(
            (e for e in _load_entries() if e.get("part_number") == part_number),
            None,
        )
        if not entry:
            continue
        title_length = _title_metric_length(entry.get("title", ""))
        if title_length is not None and title_length != length_mm:
            issues.append(
                CatalogIntegrityIssue(
                    part_number=part_number,
                    code="rule_title_length_mismatch",
                    message=(
                        f"M3 rule maps {length_mm} mm → {part_number} but title says "
                        f"{title_length} mm"
                    ),
                )
            )

    return issues
