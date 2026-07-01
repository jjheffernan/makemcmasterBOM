"""McMaster-Carr site category routing — scoped search URLs by hardware type."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

from backend.services.hardware_terms import (
    BEARING_DESIGNATION_RE,
    FASTENER_TYPE_RE,
    has_fastener_type,
    has_metric_fastener,
)
from backend.services.mcmaster_catalog import CatalogHit, mcmaster_product_url

REPO_ROOT = Path(__file__).resolve().parents[2]
CATEGORIES_PATH = REPO_ROOT / "data" / "mcmaster_categories.json"
MCMASTER_SITE_BASE = "https://www.mcmaster.com"

LinkType = Literal["product", "filtered_browse", "category_search", "site_search"]


@dataclass(frozen=True)
class McMasterCategory:
    id: str
    label: str
    route: str
    catalog_categories: tuple[str, ...]
    priority: int
    signals: tuple[str, ...]


@dataclass(frozen=True)
class CategoryMatch:
    category: McMasterCategory
    score: float
    method: str  # catalog | signal | metric | default


@dataclass(frozen=True)
class McMasterLink:
    url: str
    link_type: LinkType
    category_id: str
    category_label: str
    part_number: str = ""
    method: str = ""


@lru_cache(maxsize=1)
def _load_categories() -> tuple[McMasterCategory, ...]:
    if not CATEGORIES_PATH.is_file():
        return ()
    raw = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))
    categories: list[McMasterCategory] = []
    for item in raw.get("categories", []):
        categories.append(
            McMasterCategory(
                id=item["id"],
                label=item["label"],
                route=item["route"],
                catalog_categories=tuple(item.get("catalog_categories", [])),
                priority=int(item.get("priority", 5)),
                signals=tuple(item.get("signals", [])),
            )
        )
    return tuple(categories)


@lru_cache(maxsize=1)
def _catalog_category_index() -> dict[str, McMasterCategory]:
    index: dict[str, McMasterCategory] = {}
    for category in _load_categories():
        for name in category.catalog_categories:
            existing = index.get(name)
            if existing is None or category.priority > existing.priority:
                index[name] = category
    return index


def _default_category() -> McMasterCategory:
    raw = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))
    route = raw.get("default_route", "/products/standard-components/")
    return McMasterCategory(
        id="standard_components",
        label="Standard Components",
        route=route,
        catalog_categories=(),
        priority=0,
        signals=(),
    )


def get_category(category_id: str) -> McMasterCategory | None:
    for category in _load_categories():
        if category.id == category_id:
            return category
    if category_id == "standard_components":
        return _default_category()
    return None


def _signal_score(query: str, category: McMasterCategory) -> float:
    lower = query.lower()
    score = 0.0
    for signal in category.signals:
        if signal.startswith(" ") or signal.endswith(" "):
            if signal in lower:
                score += 1.0
            continue
        if re.search(rf"\b{re.escape(signal)}\b", lower):
            score += 1.0
    if category.id == "bearing" and BEARING_DESIGNATION_RE.search(lower):
        score += 3.0
    if category.id in {"socket_head_screw", "screw"} and has_metric_fastener(lower):
        if has_fastener_type(lower) or "screw" in lower or "bolt" in lower:
            score += 1.5
    if category.id == "nut" and re.search(r"\bnut\b", lower):
        score += 2.0
    if category.id == "washer" and re.search(r"\bwasher\b", lower):
        score += 2.0
    return score + category.priority * 0.01


def classify_category(
    query: str,
    *,
    catalog_category: str | None = None,
) -> CategoryMatch:
    """Pick the best McMaster site category for a hardware query."""
    if catalog_category:
        mapped = _catalog_category_index().get(catalog_category.lower())
        if mapped:
            return CategoryMatch(mapped, 1.0, "catalog")

    if not query or not query.strip():
        default = _default_category()
        return CategoryMatch(default, 0.0, "default")

    best: McMasterCategory | None = None
    best_score = 0.0
    for category in _load_categories():
        score = _signal_score(query, category)
        if score > best_score:
            best = category
            best_score = score

    if best and best_score >= 1.0:
        return CategoryMatch(best, min(best_score / 4.0, 1.0), "signal")

    if has_metric_fastener(query) and FASTENER_TYPE_RE.search(query):
        for category in _load_categories():
            if category.id == "socket_head_screw":
                return CategoryMatch(category, 0.6, "metric")

    default = _default_category()
    return CategoryMatch(default, 0.0, "default")


def category_search_url(category: McMasterCategory, query: str) -> str:
    encoded = quote_plus(query.strip())
    route = category.route if category.route.endswith("/") else f"{category.route}/"
    return f"{MCMASTER_SITE_BASE}{route}?searchQuery={encoded}"


def site_search_url(query: str) -> str:
    return category_search_url(_default_category(), query)


def build_mcmaster_link(
    query: str,
    *,
    catalog_hit: CatalogHit | None = None,
    part: "Part | None" = None,
) -> McMasterLink:
    """Build a product, filtered-browse, or category-scoped McMaster URL."""
    from backend.models.part import Part
    from backend.services.vendors.mcmaster.tiers import (
        resolve_mcmaster_link,
        vendor_link_to_handler_link,
    )

    resolved = resolve_mcmaster_link(
        query,
        part=part or Part(original_name=query),
        catalog_hit=catalog_hit,
    )
    return vendor_link_to_handler_link(resolved)


def list_categories() -> list[dict[str, str]]:
    return [
        {"id": c.id, "label": c.label, "route": c.route}
        for c in _load_categories()
    ]
