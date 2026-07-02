"""Structured McMaster hardware guesses — size filter, primary, same-size, wider scope."""

from __future__ import annotations

from typing import Literal

from backend.models.part import MatchAlternative, Part
from backend.services.hardware_spec import MetricFastenerSpec, primary_fastener_spec
from backend.services.vendors.base import VendorLink
from backend.services.vendors.mcmaster.browse_roots import BrowseRoot, list_finish_roots
from backend.services.vendors.mcmaster.filters import infer_finish_from_bom
from backend.services.vendors.mcmaster.metacategories import (
    bom_metacategory_matches,
    infer_bom_metacategory,
    resolve_link_metacategory,
)
from backend.services.vendors.mcmaster.urls import filtered_browse_url

GuessScope = Literal["same_size", "wider_scope"]

_SIZE_FILTER_KEYS = (
    "system-of-measurement",
    "thread-size",
    "screw-size",
    "length",
)


def filter_specificity(link: VendorLink) -> int:
    """Higher = more of the McMaster hardware catalog ruled out by URL facets."""
    path = (link.filter_path or "").lower()
    score = 0
    if "system-of-measurement~" in path:
        score += 1
    if "thread-size~" in path or "screw-size~" in path:
        score += 3
    if "length~" in path:
        score += 2
    return score


def has_size_filter(link: VendorLink) -> bool:
    path = (link.filter_path or "").lower()
    return any(key in path for key in _SIZE_FILTER_KEYS)


def classify_guess_scope(
    candidate_link: VendorLink,
    primary_link: VendorLink,
    *,
    verification_status: str | None = None,
    query: str = "",
    specification: str = "",
) -> GuessScope:
    """Bucket a secondary candidate relative to the chosen primary guess."""
    candidate_meta = resolve_link_metacategory(
        category_id=candidate_link.category_id,
        url=candidate_link.url,
    )
    meta_match = bom_metacategory_matches(candidate_meta, query, specification)
    if meta_match is False:
        return "wider_scope"

    if candidate_link.tier == "part_number":
        return "same_size"

    if candidate_link.tier in {"catalog", "rule"}:
        if verification_status in {"verified", "length_unknown"}:
            return "same_size"
        return "wider_scope"

    if candidate_link.tier == "filtered_browse":
        if candidate_link.category_id != primary_link.category_id:
            return "wider_scope"
        primary_spec = filter_specificity(primary_link)
        candidate_spec = filter_specificity(candidate_link)
        if candidate_link.filter_path == primary_link.filter_path:
            return "same_size"
        if candidate_spec >= primary_spec and candidate_spec >= 3:
            return "same_size"
        if candidate_spec > 0 and primary_spec > candidate_spec:
            return "wider_scope"
        if candidate_spec > 0:
            return "same_size"
        return "wider_scope"

    return "wider_scope"


def primary_sort_key(
    candidate: object,
    *,
    tier_rank: dict[str, int],
    query: str = "",
    specification: str = "",
) -> tuple[int, int, int, float, int]:
    """Prefer in-department, size-filtered filtered_browse, then confidence."""
    link = candidate.link  # type: ignore[attr-defined]
    tier = link.tier
    specificity = filter_specificity(link) if tier == "filtered_browse" else 0
    sized_primary = 1 if tier == "filtered_browse" and specificity >= 3 else 0
    meta = resolve_link_metacategory(category_id=link.category_id, url=link.url)
    meta_match = bom_metacategory_matches(meta, query, specification)
    department_rank = 1 if meta_match is True else 0 if meta_match is None else -1
    return (
        department_rank,
        sized_primary,
        specificity,
        candidate.confidence,  # type: ignore[attr-defined]
        -tier_rank.get(tier, 50),
    )


def build_same_size_finish_alternatives(
    query: str,
    part: Part,
    *,
    category_id: str,
    filter_path: str,
    primary_finish_id: str,
) -> list[MatchAlternative]:
    """
    Same thread/length, different McMaster material table — secondary guesses.

    Skipped when the BOM names a finish (primary already targets that material).
    """
    if not filter_path.strip():
        return []
    if infer_finish_from_bom(query, part.specification):
        return []

    alternatives: list[MatchAlternative] = []
    for root in list_finish_roots(category_id):
        if root.finish_id in {primary_finish_id, "metric"}:
            continue
        alternatives.append(_finish_root_alternative(root, category_id, filter_path, query))
    return alternatives


def _finish_root_alternative(
    root: BrowseRoot,
    category_id: str,
    filter_path: str,
    query: str,
) -> MatchAlternative:
    return MatchAlternative(
        mcmaster_url=filtered_browse_url(root.route, filter_path, search_query=query),
        mcmaster_category=category_id,
        mcmaster_metacategory=resolve_link_metacategory(category_id=category_id, url=root.route)
        or "",
        match_tier="filtered_browse",
        confidence=0.72,
        confidence_low=0.66,
        confidence_high=0.78,
        mcmaster_reason=(
            f"Same size — {root.finish_label} "
            f"(other material / finish at this thread & length)"
        ),
        guess_scope="same_size",
        guess_label=root.finish_label,
    )


def size_filter_summary(spec: MetricFastenerSpec | None) -> str:
    if not spec:
        return "hardware"
    if spec.length_mm is not None:
        return spec.label()
    if spec.diameter_mm:
        return f"{spec.label()} (length not in BOM)"
    return "hardware"
