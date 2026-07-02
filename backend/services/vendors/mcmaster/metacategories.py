"""McMaster product department (metacategory) routing — /products/{slug}/ scope."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
METACATEGORIES_PATH = REPO_ROOT / "data" / "mcmaster_metacategories.json"

_STANDARD_COMPONENTS_SLUG = "standard-components"


@dataclass(frozen=True)
class Metacategory:
    id: str
    label: str
    route: str


@lru_cache(maxsize=1)
def _load_raw() -> dict:
    if not METACATEGORIES_PATH.is_file():
        return {}
    return json.loads(METACATEGORIES_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def list_metacategories() -> tuple[Metacategory, ...]:
    raw = _load_raw()
    items: list[Metacategory] = []
    for entry in raw.get("metacategories", []):
        items.append(
            Metacategory(
                id=entry["id"],
                label=entry["label"],
                route=entry.get("route", ""),
            )
        )
    return tuple(items)


@lru_cache(maxsize=1)
def _metacategory_by_id() -> dict[str, Metacategory]:
    return {item.id: item for item in list_metacategories()}


@lru_cache(maxsize=1)
def _category_metacategory_map() -> dict[str, str]:
    return dict(_load_raw().get("category_metacategory", {}))


@lru_cache(maxsize=1)
def _product_slug_map() -> dict[str, str]:
    return dict(_load_raw().get("product_slugs", {}))


@lru_cache(maxsize=1)
def _bom_intent_signals() -> dict[str, tuple[str, ...]]:
    raw = _load_raw().get("bom_intent_signals", {})
    return {key: tuple(values) for key, values in raw.items()}


def get_metacategory(metacategory_id: str) -> Metacategory | None:
    return _metacategory_by_id().get(metacategory_id)


def metacategory_label(metacategory_id: str) -> str:
    item = get_metacategory(metacategory_id)
    return item.label if item else metacategory_id.replace("_", " ").title()


def slugs_from_product_path(path_or_url: str) -> list[str]:
    """Extract /products/{slug}/ segments from a McMaster route or URL."""
    text = path_or_url.split("?", 1)[0]
    marker = "/products/"
    idx = text.lower().find(marker)
    if idx < 0:
        return []
    tail = text[idx + len(marker) :]
    return [segment for segment in tail.split("/") if segment]


def normalize_product_slug(slug: str) -> str:
    """Collapse McMaster tile suffixes (e.g. socket-head-screws-2~) to canonical slug."""
    normalized = slug.strip().lower()
    normalized = re.sub(r"-\d+~+$", "", normalized)
    return normalized.rstrip("~")


def metacategory_for_slug(slug: str) -> str | None:
    normalized = normalize_product_slug(slug)
    if not normalized:
        return None
    mapped = _product_slug_map().get(normalized)
    if mapped:
        return mapped
    if normalized.endswith("~~"):
        base = normalized.rstrip("~")
        return _product_slug_map().get(base)
    return None


def metacategory_for_route(route: str) -> str | None:
    for slug in slugs_from_product_path(route):
        meta = metacategory_for_slug(slug)
        if meta:
            return meta
    return None


def metacategory_for_category_id(category_id: str) -> str | None:
    return _category_metacategory_map().get(category_id)


def resolve_link_metacategory(
    *,
    category_id: str = "",
    url: str = "",
    route: str = "",
) -> str | None:
    """Best department for a matcher link — category table first, then URL slug."""
    if category_id:
        meta = metacategory_for_category_id(category_id)
        if meta:
            return meta
    for path in (url, route):
        if path:
            meta = metacategory_for_route(path)
            if meta:
                return meta
    return None


def metacategory_for_url(url: str) -> str | None:
    return metacategory_for_route(url)


def is_standard_components_route(route_or_url: str) -> bool:
    return _STANDARD_COMPONENTS_SLUG in [
        slug.lower() for slug in slugs_from_product_path(route_or_url)
    ]


def _keyword_hits(text: str, keywords: tuple[str, ...]) -> list[str]:
    lower = text.lower()
    hits: list[str] = []
    for keyword in keywords:
        if " " in keyword or "-" in keyword:
            if keyword in lower:
                hits.append(keyword)
            continue
        if re.search(rf"\b{re.escape(keyword)}\b", lower):
            hits.append(keyword)
    return hits


def infer_bom_metacategory(query: str, specification: str = "") -> str | None:
    """
    Guess which McMaster department a BOM line belongs in.

    Used to prefer in-department browse tables and demote cross-department guesses.
    """
    text = f"{query} {specification}".strip().lower()
    if not text:
        return None

    scored: list[tuple[str, int]] = []
    for meta_id, keywords in _bom_intent_signals().items():
        hits = _keyword_hits(text, keywords)
        if hits:
            scored.append((meta_id, len(hits)))

    if not scored:
        return None

    scored.sort(key=lambda row: row[1], reverse=True)
    best_id, best_score = scored[0]
    if len(scored) > 1 and scored[1][1] == best_score:
        return None
    return best_id


def bom_metacategory_matches(
    metacategory_id: str | None,
    query: str,
    specification: str = "",
) -> bool | None:
    """
    True when the link's department matches BOM intent.

    None when intent is ambiguous or unknown.
    """
    if not metacategory_id:
        return None
    expected = infer_bom_metacategory(query, specification)
    if not expected:
        return None
    return metacategory_id == expected


def metacategory_mismatch_note(
    *,
    actual_id: str | None,
    query: str,
    specification: str = "",
) -> str | None:
    expected = infer_bom_metacategory(query, specification)
    if not expected or not actual_id or expected == actual_id:
        return None
    return (
        f"McMaster department mismatch — link is "
        f"{metacategory_label(actual_id)}; BOM suggests "
        f"{metacategory_label(expected)}"
    )
