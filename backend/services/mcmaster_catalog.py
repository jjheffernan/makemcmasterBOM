"""Curated McMaster part-number catalog and lookup helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from backend.services.hardware_terms import (
    BEARING_DESIGNATION_RE,
    METRIC_FASTENER_RE,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "data" / "mcmaster_catalog.json"
MCMASTER_PRODUCT_BASE = "https://www.mcmaster.com/"

# M3 socket head cap screw (black-oxide alloy steel, 91290A series) by length
M3_SOCKET_HEAD_BY_LENGTH_MM: dict[int, str] = {
    6: "91290A109",
    8: "91290A110",
    10: "91290A111",
    12: "91290A112",
    16: "91290A120",
    20: "91290A114",
    25: "91290A115",
    30: "91290A116",
}

BEARING_TRADE_DEFAULTS: dict[str, tuple[str, str]] = {
    "608": ("5972K113", "608 Double-Shielded Ball Bearing"),
    "693": ("5972K42", "693 Double-Shielded Ball Bearing"),
}


@dataclass(frozen=True)
class CatalogHit:
    part_number: str
    title: str
    category: str
    source: str  # "catalog" | "rule"


def normalize_catalog_key(text: str) -> str:
    """Normalize a BOM line or search query for catalog key lookup."""
    key = text.lower().strip()
    key = re.sub(r"\s+", " ", key)
    key = METRIC_FASTENER_RE.sub(
        lambda m: f"m{float(m.group(1)):g}x{float(m.group(2)):g}",
        key,
    )
    key = re.sub(r"\bm(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*mm\b", r"m\1-\2", key)
    key = re.sub(r"\b(\d+)\s*mm\b", r"\1mm", key)
    key = re.sub(r"\s*-\s*", "-", key)
    return key.strip()


def mcmaster_product_url(part_number: str, search_query: str = "") -> str:
    """
    McMaster product detail URL.

    With a search query, opens the specific part page with context:
    https://www.mcmaster.com/90273A010/?searchQuery=M3x25+screw
    """
    pn = part_number.strip()
    query = search_query.strip()
    if query:
        return f"{MCMASTER_PRODUCT_BASE}{pn}/?searchQuery={quote_plus(query)}"
    return f"{MCMASTER_PRODUCT_BASE}{pn}"


@lru_cache(maxsize=1)
def _load_key_index() -> dict[str, CatalogHit]:
    if not CATALOG_PATH.is_file():
        return {}
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    index: dict[str, CatalogHit] = {}
    for entry in raw.get("entries", []):
        hit = CatalogHit(
            part_number=entry["part_number"],
            title=entry.get("title", entry["part_number"]),
            category=entry.get("category", "hardware"),
            source="catalog",
        )
        for key in entry.get("keys", []):
            index[normalize_catalog_key(key)] = hit
    return index


def _lookup_catalog_keys(query: str) -> CatalogHit | None:
    key = normalize_catalog_key(query)
    index = _load_key_index()
    if key in index:
        return index[key]
    # Allow trailing material words: "m3x8 socket head cap screw stainless"
    words = key.split()
    for end in range(len(words), 2, -1):
        partial = " ".join(words[:end])
        if partial in index:
            return index[partial]
    return None


def _lookup_rules(query: str) -> CatalogHit | None:
    lower = query.lower()

    bearing = BEARING_DESIGNATION_RE.search(lower)
    if bearing:
        trade = re.sub(r"[^0-9]", "", bearing.group(0)[:3])
        if trade in BEARING_TRADE_DEFAULTS:
            part_number, title = BEARING_TRADE_DEFAULTS[trade]
            if re.search(r"(?:zz|2z|2rs|rs)\b", lower):
                return CatalogHit(
                    part_number=part_number,
                    title=title,
                    category="bearing",
                    source="rule",
                )

    metric = METRIC_FASTENER_RE.search(lower)
    if metric:
        diameter = float(metric.group(1))
        length_mm = int(float(metric.group(2)))
        is_socket_head = "socket" in lower and "head" in lower
        is_cap_screw = "cap screw" in lower or "socket head cap screw" in lower
        is_plain_metric_screw = (
            "nut" not in lower
            and "washer" not in lower
            and "bearing" not in lower
            and "insert" not in lower
        )
        if diameter == 3 and (
            is_socket_head or is_cap_screw or is_plain_metric_screw
        ):
            part_number = M3_SOCKET_HEAD_BY_LENGTH_MM.get(length_mm)
            if part_number:
                return CatalogHit(
                    part_number=part_number,
                    title=f"M3 × {length_mm} mm Socket Head Screw, Black-Oxide Alloy Steel",
                    category="screw",
                    source="rule",
                )

    if re.search(r"\bm3\b", lower) and re.search(r"\bhex\s+nut\b", lower):
        return CatalogHit(
            part_number="91828A113",
            title="M3 Hex Nut, 18-8 Stainless Steel",
            category="nut",
            source="rule",
        )

    if re.search(r"\bm3\b", lower) and re.search(r"\bwasher\b", lower):
        return CatalogHit(
            part_number="98689A113",
            title="M3 Washer, 18-8 Stainless Steel",
            category="washer",
            source="rule",
        )

    return None


def catalog_lookup(query: str) -> CatalogHit | None:
    """Resolve a normalized hardware query to a McMaster catalog part number."""
    if not query or not query.strip():
        return None
    stripped = re.sub(r"^\d+(?:\.\d+)?\s*[x×]\s*", "", query.strip(), flags=re.I)
    for candidate in (query, stripped):
        hit = _lookup_catalog_keys(candidate) or _lookup_rules(candidate)
        if hit:
            return hit
    return None


def catalog_stats() -> dict[str, int]:
    index = _load_key_index()
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8")) if CATALOG_PATH.is_file() else {}
    return {
        "entries": len(raw.get("entries", [])),
        "keys": len(index),
    }
