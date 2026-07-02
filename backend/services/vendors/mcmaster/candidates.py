"""Multi-candidate McMaster matching — rank filtered browse above catalog SKUs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend import config
from backend.models.part import MatchAlternative, Part
from backend.services.hardware_match_verify import (
    HardwareMatchCheck,
    verify_hardware_match,
)
from backend.services.hardware_spec import MetricFastenerSpec, primary_fastener_spec
from backend.services.mcmaster_catalog import CatalogHit, catalog_lookup
from backend.services.mcmaster_handler import classify_category
from backend.services.vendors.base import MatchTier, VendorLink
from backend.services.vendors.mcmaster.filters import infer_material_variant_id
from backend.services.vendors.mcmaster.metacategories import (
    metacategory_label,
    resolve_link_metacategory,
)
from backend.services.vendors.mcmaster.tiers import (
    _try_explicit_part_number,
    _try_filtered_browse,
    _try_metric_category_browse,
    _vendor_link_from_catalog,
)
from backend.services.vendors.mcmaster.guess_strategy import (
    build_same_size_finish_alternatives,
    classify_guess_scope,
    primary_sort_key,
)
from backend.services.vendors.mcmaster.urls import category_search_url

_GUESS_LABELS = {
    "catalog": "Catalog SKU",
    "rule": "Length rule",
    "part_number": "BOM part #",
    "filtered_browse": "Filtered table",
    "category_search": "Category table",
}

_TIER_RANK: dict[MatchTier, int] = {
    "filtered_browse": 0,
    "part_number": 1,
    "catalog": 2,
    "rule": 3,
    "api_verified": 4,
    "category_search": 5,
    "site_search": 6,
    "not_applicable": 99,
}

_CATALOG_STAINLESS = re.compile(r"\b(18-8|316|stainless)\b", re.I)
_CATALOG_BLACK_OXIDE = re.compile(r"\b(black[\s-]*oxide|alloy\s+steel)\b", re.I)


@dataclass(frozen=True)
class ScoredCandidate:
    link: VendorLink
    catalog_hit: CatalogHit | None
    confidence: float
    confidence_low: float
    confidence_high: float
    reason: str
    verification: HardwareMatchCheck | None = None

    def to_alternative(self, *, guess_scope: str = "wider_scope") -> MatchAlternative:
        tier = self.link.tier
        label = _GUESS_LABELS.get(tier, tier.replace("_", " ").title())
        finish = self.link.extras.get("browse_finish")
        if finish and guess_scope == "same_size":
            label = str(self.link.extras.get("finish_label") or finish).replace("_", " ")
        meta_id = resolve_link_metacategory(
            category_id=self.link.category_id,
            url=self.link.url,
        )
        return MatchAlternative(
            mcmaster_url=self.link.url,
            mcmaster_part_number=self.link.part_number,
            mcmaster_category=self.link.category_id,
            mcmaster_metacategory=meta_id or "",
            mcmaster_metacategory_label=metacategory_label(meta_id) if meta_id else "",
            match_tier=self.link.tier,
            confidence=self.confidence,
            confidence_low=self.confidence_low,
            confidence_high=self.confidence_high,
            mcmaster_reason=self.reason,
            guess_scope=guess_scope,
            guess_label=label,
        )


def bom_material_matches_catalog(
    hit: CatalogHit,
    query: str,
    specification: str,
) -> bool | None:
    """True/False when BOM material conflicts with catalog title; None if unknown."""
    bom_material = infer_material_variant_id(
        query,
        specification,
        category_id=hit.category,
    )
    title = hit.title.lower()

    catalog_stainless = bool(_CATALOG_STAINLESS.search(title))
    catalog_black = bool(_CATALOG_BLACK_OXIDE.search(title))

    if bom_material == "stainless":
        if catalog_stainless:
            return True
        if catalog_black:
            return False
        return None
    if bom_material == "black_oxide":
        if catalog_black:
            return True
        if catalog_stainless:
            return False
        return None
    if bom_material == "steel" and catalog_stainless:
        return None
    return None


_FINISH_LABELS = {
    "black_oxide": "black oxide",
    "zinc_plated": "zinc plated",
    "stainless": "18-8 stainless",
}


def _score_filtered_browse(
    link: VendorLink,
    spec: MetricFastenerSpec | None,
) -> tuple[float, float, float, str]:
    finish = link.extras.get("browse_finish", "black_oxide")
    finish_note = f" ({_FINISH_LABELS.get(finish, finish)})" if finish else ""

    if spec and spec.diameter_mm and spec.length_mm is not None:
        return (
            0.92,
            0.88,
            0.96,
            f"Primary guess — filtered McMaster table for {spec.label()}{finish_note}",
        )
    if spec and spec.diameter_mm:
        if spec.kind in {"nut", "washer"}:
            return (
                0.86,
                0.82,
                0.90,
                f"Primary guess — filtered McMaster table for {spec.label()}{finish_note}",
            )
        return (
            0.82,
            0.76,
            0.86,
            f"Primary guess — metric thread {spec.label()} (length not in BOM){finish_note}",
        )
    return 0.70, 0.65, 0.75, f"Primary guess — McMaster {link.category_label} filtered browse"


def _score_catalog(
    hit: CatalogHit,
    link: VendorLink,
    part: Part,
    query: str,
    check: HardwareMatchCheck,
) -> tuple[float, float, float, str]:
    title = hit.title
    tier_label = "rule" if hit.source == "rule" else "catalog"
    base_reason = f"Catalog SKU guess — {title}"

    if check.status in {"size_mismatch", "length_mismatch", "spec_conflict"}:
        return 0.42, 0.35, 0.48, f"{check.message}. {base_reason}"

    material = bom_material_matches_catalog(hit, query, part.specification)
    inferred_rule = hit.source == "rule"

    if check.status == "verified":
        if material is True:
            return (
                0.84,
                0.80,
                0.88,
                f"Catalog SKU guess — {title} (size/length OK; verify on filtered table)",
            )
        if material is False:
            return (
                0.55,
                0.50,
                0.62,
                f"Catalog SKU may be wrong material — {title}. Prefer filtered browse.",
            )
        if inferred_rule:
            return (
                0.72,
                0.66,
                0.78,
                f"Inferred {tier_label} match — {title} (verify head style & finish)",
            )
        return 0.82, 0.76, 0.88, f"Catalog SKU — {title} (size/length OK; verify finish)"

    if check.status == "length_unknown":
        if inferred_rule:
            return 0.68, 0.62, 0.74, f"Inferred SKU — {title} (length not verified)"
        return 0.72, 0.66, 0.78, f"Catalog SKU — {title} (length not in BOM)"

    material = bom_material_matches_catalog(hit, query, part.specification)
    if material is True:
        return 0.88, 0.84, 0.92, f"Catalog match — {title} (material OK)"
    if material is False:
        return (
            0.55,
            0.50,
            0.62,
            f"Catalog SKU may be wrong material — {title}. Prefer filtered browse.",
        )
    if inferred_rule:
        return 0.68, 0.62, 0.74, f"Inferred {tier_label} match — {title}"

    return 0.78, 0.72, 0.84, f"Catalog SKU — {title}"


def _score_part_number(link: VendorLink) -> tuple[float, float, float, str]:
    return (
        0.93,
        0.90,
        0.96,
        f"McMaster part number found in BOM — {link.part_number}",
    )


def _score_category_search(link: VendorLink) -> tuple[float, float, float, str]:
    if link.method == "metric_category_browse" and link.filter_path:
        return (
            0.58,
            0.52,
            0.64,
            f"Wider search — McMaster {link.category_label} metric thread table",
        )
    return (
        0.48,
        0.42,
        0.54,
        f"Wider search — McMaster {link.category_label} category browse",
    )


def _score_site_search() -> tuple[float, float, float, str]:
    return 0.32, 0.25, 0.40, "McMaster site-wide search"


def _catalog_hit_for_part(query: str, part: Part) -> CatalogHit | None:
    spec_text = part.specification.strip()
    candidates = [query]
    if spec_text:
        candidates.insert(0, f"{query} {spec_text}".strip())
        candidates.append(f"{part.original_name} {spec_text}".strip())
    for candidate in candidates:
        hit = catalog_lookup(candidate)
        if hit:
            return hit
    return None


def _collect_vendor_links(
    query: str,
    part: Part,
    catalog_hit: CatalogHit | None,
) -> list[tuple[VendorLink, CatalogHit | None]]:
    category_match = classify_category(
        query,
        catalog_category=catalog_hit.category if catalog_hit else None,
    )
    collected: list[tuple[VendorLink, CatalogHit | None]] = []
    seen_urls: set[str] = set()

    def add(link: VendorLink, hit: CatalogHit | None = None) -> None:
        if link.url in seen_urls:
            return
        seen_urls.add(link.url)
        collected.append((link, hit))

    filtered = _try_filtered_browse(query, part, category_match)
    if filtered:
        add(filtered)

    explicit = _try_explicit_part_number(query, part)
    if explicit:
        add(explicit)

    use_live_table = config.MCMASTER_BROWSE_RESOLVE_ENABLED and filtered is not None
    if catalog_hit:
        catalog_link = _vendor_link_from_catalog(query, catalog_hit, category_match)
        if use_live_table:
            catalog_link = VendorLink(
                url=catalog_link.url,
                link_kind=catalog_link.link_kind,
                tier=catalog_link.tier,
                part_number=catalog_link.part_number,
                category_id=catalog_link.category_id,
                category_label=catalog_link.category_label,
                filter_path=catalog_link.filter_path,
                method="catalog_cache",
                confidence_hint=0.65,
                extras=catalog_link.extras,
            )
        add(catalog_link, catalog_hit)

    if category_match.method in {"default", "unclassified"}:
        pass
    else:
        metric_category = _try_metric_category_browse(query, part, category_match)
        if metric_category:
            add(
                VendorLink(
                    url=metric_category.url,
                    link_kind="filtered_browse",
                    tier="category_search",
                    category_id=metric_category.category_id,
                    category_label=metric_category.category_label,
                    filter_path=metric_category.filter_path,
                    method="metric_category_browse",
                    confidence_hint=0.62,
                )
            )
        else:
            add(
                VendorLink(
                    url=category_search_url(category_match.category.route, query),
                    link_kind="category_search",
                    tier="category_search",
                    category_id=category_match.category.id,
                    category_label=category_match.category.label,
                    method=category_match.method,
                    confidence_hint=0.55,
                )
            )

    return collected


def _score_link(
    link: VendorLink,
    hit: CatalogHit | None,
    part: Part,
    query: str,
) -> ScoredCandidate:
    spec = primary_fastener_spec(part)

    if link.tier in {"catalog", "rule"} and hit:
        check = verify_hardware_match(part, hit=hit)
        conf, low, high, reason = _score_catalog(hit, link, part, query, check)
        if link.method == "catalog_cache":
            conf = min(conf, 0.72)
            low = min(low, 0.66)
            high = min(high, 0.78)
            reason = f"Cached catalog fallback — {reason}"
        return ScoredCandidate(
            link=link,
            catalog_hit=hit,
            confidence=conf,
            confidence_low=low,
            confidence_high=high,
            reason=reason,
            verification=check,
        )

    if link.tier == "part_number":
        conf, low, high, reason = _score_part_number(link)
    elif link.tier == "filtered_browse":
        conf, low, high, reason = _score_filtered_browse(link, spec)
    elif link.tier == "category_search":
        conf, low, high, reason = _score_category_search(link)
    else:
        conf, low, high, reason = _score_site_search()

    return ScoredCandidate(
        link=link,
        catalog_hit=None,
        confidence=conf,
        confidence_low=low,
        confidence_high=high,
        reason=reason,
    )


def _sort_candidates(candidates: list[ScoredCandidate]) -> list[ScoredCandidate]:
    return sorted(
        candidates,
        key=lambda c: (
            -c.confidence,
            _TIER_RANK.get(c.link.tier, 50),
        ),
    )


def collect_scored_candidates(
    query: str,
    part: Part,
) -> list[ScoredCandidate]:
    """Generate and rank all offline McMaster link candidates for a BOM line."""
    catalog_hit = _catalog_hit_for_part(query, part)
    links = _collect_vendor_links(query, part, catalog_hit)
    links = [
        (link, hit)
        for link, hit in links
        if link.tier not in {"site_search", "not_applicable"} and link.url.strip()
    ]
    scored = [_score_link(link, hit, part, query) for link, hit in links]
    return _sort_candidates(scored)


def pick_primary_and_alternatives(
    candidates: list[ScoredCandidate],
    *,
    query: str = "",
    part: Part | None = None,
    max_same_size: int = 3,
    max_wider_scope: int = 3,
) -> tuple[ScoredCandidate | None, list[ScoredCandidate]]:
    if not candidates:
        return None, []

    specification = part.specification if part else ""
    ranked = sorted(
        candidates,
        key=lambda c: primary_sort_key(
            c,
            tier_rank=_TIER_RANK,
            query=query,
            specification=specification,
        ),
        reverse=True,
    )
    primary = ranked[0]
    remainder = [c for c in ranked if c.link.url != primary.link.url]

    same_size: list[ScoredCandidate] = []
    wider_scope: list[ScoredCandidate] = []
    for candidate in remainder:
        scope = classify_guess_scope(
            candidate.link,
            primary.link,
            verification_status=(
                candidate.verification.status if candidate.verification else None
            ),
            query=query,
            specification=specification,
        )
        if scope == "same_size":
            same_size.append(candidate)
        else:
            wider_scope.append(candidate)

    if part and primary.link.tier == "filtered_browse" and primary.link.filter_path:
        primary_finish = str(primary.link.extras.get("browse_finish", ""))
        finish_alts = build_same_size_finish_alternatives(
            query,
            part,
            category_id=primary.link.category_id,
            filter_path=primary.link.filter_path,
            primary_finish_id=primary_finish,
        )
        existing_urls = {primary.link.url} | {c.link.url for c in same_size}
        for alt in finish_alts:
            if alt.mcmaster_url in existing_urls:
                continue
            existing_urls.add(alt.mcmaster_url)
            same_size.append(
                ScoredCandidate(
                    link=VendorLink(
                        url=alt.mcmaster_url,
                        link_kind="filtered_browse",
                        tier="filtered_browse",
                        category_id=alt.mcmaster_category,
                        category_label=primary.link.category_label,
                        filter_path=primary.link.filter_path,
                        method="finish_alternate",
                        confidence_hint=alt.confidence,
                        extras={
                            "browse_finish": alt.guess_label,
                            "finish_label": alt.guess_label,
                        },
                    ),
                    catalog_hit=None,
                    confidence=alt.confidence,
                    confidence_low=alt.confidence_low or alt.confidence,
                    confidence_high=alt.confidence_high or alt.confidence,
                    reason=alt.mcmaster_reason,
                )
            )

    same_size.sort(
        key=lambda c: (-c.confidence, _TIER_RANK.get(c.link.tier, 50)),
    )
    wider_scope.sort(
        key=lambda c: (-c.confidence, _TIER_RANK.get(c.link.tier, 50)),
    )

    structured: list[ScoredCandidate] = []
    structured.extend(same_size[:max_same_size])
    structured.extend(wider_scope[:max_wider_scope])
    return primary, structured


def alternatives_with_scope(
    alt_candidates: list[ScoredCandidate],
    primary: ScoredCandidate,
    *,
    query: str = "",
    specification: str = "",
) -> list[MatchAlternative]:
    results: list[MatchAlternative] = []
    for candidate in alt_candidates:
        scope = classify_guess_scope(
            candidate.link,
            primary.link,
            verification_status=(
                candidate.verification.status if candidate.verification else None
            ),
            query=query,
            specification=specification,
        )
        results.append(candidate.to_alternative(guess_scope=scope))
    return results
