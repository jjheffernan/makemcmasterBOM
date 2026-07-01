"""Multi-candidate McMaster matching — rank filtered browse above catalog SKUs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.models.part import MatchAlternative, Part
from backend.services.hardware_match_verify import (
    HardwareMatchCheck,
    verify_hardware_match,
)
from backend.services.hardware_spec import MetricFastenerSpec, primary_fastener_spec
from backend.services.mcmaster_catalog import CatalogHit, catalog_lookup
from backend.services.mcmaster_handler import classify_category, site_search_url
from backend.services.vendors.base import MatchTier, VendorLink
from backend.services.vendors.mcmaster.filters import infer_material_variant_id
from backend.services.vendors.mcmaster.tiers import (
    _try_explicit_part_number,
    _try_filtered_browse,
    _vendor_link_from_catalog,
)
from backend.services.vendors.mcmaster.urls import category_search_url

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

    def to_alternative(self) -> MatchAlternative:
        return MatchAlternative(
            mcmaster_url=self.link.url,
            mcmaster_part_number=self.link.part_number,
            mcmaster_category=self.link.category_id,
            match_tier=self.link.tier,
            confidence=self.confidence,
            confidence_low=self.confidence_low,
            confidence_high=self.confidence_high,
            mcmaster_reason=self.reason,
        )


def bom_material_matches_catalog(
    hit: CatalogHit,
    query: str,
    specification: str,
) -> bool | None:
    """True/False when BOM material conflicts with catalog title; None if unknown."""
    bom_material = infer_material_variant_id(query, specification)
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
            0.90,
            0.86,
            0.94,
            f"Best guess — McMaster filtered table for {spec.label()}{finish_note}",
        )
    if spec and spec.diameter_mm:
        return (
            0.78,
            0.72,
            0.82,
            f"Filtered browse — metric thread {spec.label()} (length not in BOM){finish_note}",
        )
    return 0.70, 0.65, 0.75, f"McMaster {link.category_label} filtered browse"


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
    return 0.52, 0.45, 0.58, f"McMaster {link.category_label} category search"


def _score_site_search() -> tuple[float, float, float, str]:
    return 0.32, 0.25, 0.40, "McMaster site-wide search"


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

    if catalog_hit:
        add(_vendor_link_from_catalog(query, catalog_hit, category_match), catalog_hit)

    explicit = _try_explicit_part_number(query, part)
    if explicit:
        add(explicit)

    filtered = _try_filtered_browse(query, part, category_match)
    if filtered:
        add(filtered)

    if category_match.method == "default":
        add(
            VendorLink(
                url=site_search_url(query),
                link_kind="site_search",
                tier="site_search",
                category_id=category_match.category.id,
                category_label=category_match.category.label,
                method="default",
                confidence_hint=0.35,
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
    catalog_hit = catalog_lookup(query)
    links = _collect_vendor_links(query, part, catalog_hit)
    scored = [_score_link(link, hit, part, query) for link, hit in links]
    return _sort_candidates(scored)


def pick_primary_and_alternatives(
    candidates: list[ScoredCandidate],
    *,
    max_alternatives: int = 4,
) -> tuple[ScoredCandidate | None, list[ScoredCandidate]]:
    if not candidates:
        return None, []
    primary = candidates[0]
    alternatives = candidates[1 : max_alternatives + 1]
    return primary, alternatives
