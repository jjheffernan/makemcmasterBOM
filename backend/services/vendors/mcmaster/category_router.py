"""McMaster product-category routing — prefer broad catalogs, escape via keywords."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from backend.services.hardware_terms import (
    FASTENER_TYPE_RE,
    has_fastener_type,
    has_metric_fastener,
)
from backend.services.mcmaster_handler import (
    McMasterCategory,
    _FLAT_HEAD_QUERY_RE,
    _SOCKET_HEAD_QUERY_RE,
    _default_category,
    _load_categories,
    get_category,
    infer_screw_head_type,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
ROUTING_PATH = REPO_ROOT / "data" / "mcmaster_category_routing.json"


@dataclass(frozen=True)
class RoutedCategory:
    category: McMasterCategory
    score: float
    method: str
    matched_keywords: tuple[str, ...] = ()


@lru_cache(maxsize=1)
def _load_routing_meta() -> dict[str, dict]:
    if not ROUTING_PATH.is_file():
        return {}
    raw = json.loads(ROUTING_PATH.read_text(encoding="utf-8"))
    return {entry["category_id"]: entry for entry in raw.get("categories", [])}


def _meta_for(category_id: str) -> dict:
    return _load_routing_meta().get(category_id, {})


def _keyword_hits(query: str, keywords: tuple[str, ...]) -> list[str]:
    lower = query.lower()
    hits: list[str] = []
    for keyword in keywords:
        if keyword.startswith(" ") or keyword.endswith(" "):
            if keyword in lower:
                hits.append(keyword.strip())
            continue
        if re.search(rf"\b{re.escape(keyword)}\b", lower):
            hits.append(keyword)
    return hits


def _signal_score(query: str, category: McMasterCategory) -> float:
    from backend.services.mcmaster_handler import _signal_score as handler_signal_score

    return handler_signal_score(query, category)


def _escape_score(query: str, category_id: str) -> tuple[float, tuple[str, ...]]:
    meta = _meta_for(category_id)
    escape = tuple(meta.get("escape_keywords", ()))
    hits = _keyword_hits(query, escape)
    if not hits:
        return 0.0, ()
    return float(len(hits)) * 2.5, tuple(hits)


def _catalog_size_bonus(category_id: str) -> float:
    meta = _meta_for(category_id)
    size = int(meta.get("catalog_size", 0))
    if size <= 0:
        return 0.0
    return math.log10(size) * 0.35


def route_category(
    query: str,
    *,
    catalog_category: str | None = None,
) -> RoutedCategory:
    """
    Pick a McMaster browse category.

    Prefer larger product catalogs when the query is ambiguous; use escape
    keywords to narrow broad parents (e.g. screws → flat-head vs socket-head).
    """
    if not query or not query.strip():
        default = _default_category()
        return RoutedCategory(default, 0.0, "unclassified")

    head_type = infer_screw_head_type(query)
    if head_type == "flat_head":
        flat = get_category("flat_head_screw")
        if flat:
            hits = _keyword_hits(query, flat.signals)
            return RoutedCategory(
                flat,
                0.9,
                "head_type",
                tuple(hits),
            )

    if catalog_category and head_type != "flat_head":
        from backend.services.mcmaster_handler import _catalog_category_index

        mapped = _catalog_category_index().get(catalog_category.lower())
        if mapped and mapped.id != "screw":
            return RoutedCategory(mapped, 1.0, "catalog")
        if mapped and mapped.id == "screw" and head_type == "socket_head":
            socket = get_category("socket_head_screw")
            if socket:
                return RoutedCategory(socket, 1.0, "catalog")

    scored: list[tuple[McMasterCategory, float, str, tuple[str, ...]]] = []
    for category in _load_categories():
        signal = _signal_score(query, category)
        escape, escape_hits = _escape_score(query, category.id)
        passive_priority = category.priority * 0.01
        keyword_signal = max(0.0, signal - passive_priority)
        relevance = keyword_signal + escape
        if relevance < 1.0:
            continue

        size_bonus = _catalog_size_bonus(category.id)
        total = relevance + size_bonus

        if category.id == "socket_head_screw" and _FLAT_HEAD_QUERY_RE.search(query):
            total -= 4.0
        if category.id == "screw" and _FLAT_HEAD_QUERY_RE.search(query):
            total -= 1.0
        if category.id == "flat_head_screw" and _SOCKET_HEAD_QUERY_RE.search(query):
            total -= 2.0

        if total > 0:
            method = "escape" if escape_hits else "signal"
            scored.append((category, total, method, escape_hits))

    if scored:
        scored.sort(key=lambda row: row[1], reverse=True)
        best, best_score, method, hits = scored[0]

        if (
            best.id == "screw"
            and has_metric_fastener(query)
            and head_type is None
            and re.search(r"\b(screw|shcs)\b", query, re.I)
            and not re.search(r"\bbolt\b", query, re.I)
        ):
            socket = get_category("socket_head_screw")
            if socket:
                return RoutedCategory(socket, 0.65, "metric_default")

        return RoutedCategory(
            best,
            min(best_score / 4.0, 1.0),
            method,
            hits,
        )

    if has_metric_fastener(query) and FASTENER_TYPE_RE.search(query):
        if head_type != "flat_head":
            socket = get_category("socket_head_screw")
            if socket:
                return RoutedCategory(socket, 0.6, "metric")

    default = _default_category()
    return RoutedCategory(default, 0.0, "unclassified")
