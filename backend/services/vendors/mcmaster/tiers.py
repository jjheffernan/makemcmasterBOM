"""Tiered McMaster link resolution — catalog → rules → part# → filtered browse → search."""

from __future__ import annotations

from backend import config
from backend.models.part import Part
from backend.services.hardware_spec import MetricFastenerSpec, primary_fastener_spec
from backend.services.mcmaster_catalog import CatalogHit, catalog_lookup
from backend.services.mcmaster_handler import (
    CategoryMatch,
    McMasterLink,
    classify_category,
)
from backend.services.vendors.mcmaster.urls import (
    category_search_url,
    filtered_browse_url,
    mcmaster_product_url,
)
from backend.services.vendors.base import MatchTier, VendorLink, VendorMatchContext
from backend.services.vendors.mcmaster.browse_roots import get_browse_root
from backend.services.vendors.mcmaster.filters import (
    build_fastener_filters,
    infer_material_variant_id,
)
from backend.services.vendors.mcmaster.part_numbers import (
    extract_part_number_from_text,
    is_valid_part_number,
)

_FILTERED_BROWSE_CATEGORIES = frozenset(
    {"socket_head_screw", "flat_head_screw", "screw", "nut", "washer"},
)


def _catalog_hit_tier(hit: CatalogHit) -> MatchTier:
    return "rule" if hit.source == "rule" else "catalog"


def _vendor_link_from_catalog(
    query: str,
    hit: CatalogHit,
    category_match: CategoryMatch,
) -> VendorLink:
    return VendorLink(
        url=mcmaster_product_url(hit.part_number, query),
        link_kind="product",
        tier=_catalog_hit_tier(hit),
        part_number=hit.part_number,
        category_id=category_match.category.id,
        category_label=category_match.category.label,
        method="catalog",
        confidence_hint=1.0,
        extras={"catalog_title": hit.title},
    )


def _build_filtered_browse_link(
    query: str,
    part: Part,
    category_match: CategoryMatch,
    spec: MetricFastenerSpec,
    *,
    finish_id: str,
    method: str = "filtered_browse",
) -> VendorLink | None:
    filters = build_fastener_filters(spec)
    if filters.is_empty or spec.diameter_mm is None:
        return None

    browse_root = get_browse_root(category_match.category.id, finish_id)
    if not browse_root:
        return None

    url = filtered_browse_url(
        browse_root.route,
        filters.as_path(),
        search_query=query,
    )
    return VendorLink(
        url=url,
        link_kind="filtered_browse",
        tier="filtered_browse",
        category_id=category_match.category.id,
        category_label=category_match.category.label,
        filter_path=filters.as_path(),
        method=method,
        confidence_hint=0.75,
        extras={"browse_finish": finish_id},
    )


def _try_filtered_browse(
    query: str,
    part: Part,
    category_match: CategoryMatch,
) -> VendorLink | None:
    if not config.MCMASTER_FILTERED_BROWSE_ENABLED:
        return None
    if category_match.category.id not in _FILTERED_BROWSE_CATEGORIES:
        return None

    spec: MetricFastenerSpec | None = primary_fastener_spec(part)
    if not spec or spec.diameter_mm is None:
        return None

    finish_id = infer_material_variant_id(
        query,
        part.specification,
        category_id=category_match.category.id,
    )
    link = _build_filtered_browse_link(
        query,
        part,
        category_match,
        spec,
        finish_id=finish_id,
    )
    if link:
        return link

    for fallback in ("black_oxide", "zinc_plated", "stainless"):
        if fallback == finish_id:
            continue
        link = _build_filtered_browse_link(
            query,
            part,
            category_match,
            spec,
            finish_id=fallback,
        )
        if link:
            return link
    return None


def _try_metric_category_browse(
    query: str,
    part: Part,
    category_match: CategoryMatch,
) -> VendorLink | None:
    """Thread-filtered category table — closer to products than ?searchQuery= on category."""
    if not config.MCMASTER_FILTERED_BROWSE_ENABLED:
        return None
    if category_match.category.id not in _FILTERED_BROWSE_CATEGORIES:
        return None

    spec = primary_fastener_spec(part)
    if not spec or spec.diameter_mm is None:
        return None

    link = _build_filtered_browse_link(
        query,
        part,
        category_match,
        spec,
        finish_id="metric",
        method="metric_category_browse",
    )
    if not link:
        return None
    return VendorLink(
        url=link.url,
        link_kind="filtered_browse",
        tier="category_search",
        category_id=link.category_id,
        category_label=link.category_label,
        filter_path=link.filter_path,
        method="metric_category_browse",
        confidence_hint=0.62,
        extras=link.extras,
    )


def _try_explicit_part_number(query: str, part: Part) -> VendorLink | None:
    combined = f"{part.original_name} {part.specification} {part.notes}"
    part_number = extract_part_number_from_text(combined)
    if not part_number or not is_valid_part_number(part_number):
        return None
    category_match = classify_category(query)
    return VendorLink(
        url=mcmaster_product_url(part_number, query),
        link_kind="product",
        tier="part_number",
        part_number=part_number,
        category_id=category_match.category.id,
        category_label=category_match.category.label,
        method="part_number",
        confidence_hint=0.95,
    )


def resolve_mcmaster_link(
    query: str,
    *,
    part: Part | None = None,
    catalog_hit: CatalogHit | None = None,
) -> VendorLink:
    """
    Resolve the best McMaster outbound link without live network calls.

    Tier order:
      1. Curated catalog JSON
      2. Rule engine (M3 length table, bearing trade numbers, …)
      3. Explicit part number in BOM text
      4. Filtered category browse URL (metric thread + length facets)
      5. Category-scoped search
      6. Site-wide search
    """
    part = part or Part(original_name=query)
    category_match = classify_category(
        query,
        catalog_category=catalog_hit.category if catalog_hit else None,
    )

    if catalog_hit:
        return _vendor_link_from_catalog(query, catalog_hit, category_match)

    explicit = _try_explicit_part_number(query, part)
    if explicit:
        return explicit

    filtered = _try_filtered_browse(query, part, category_match)
    if filtered:
        return filtered

    metric_category = _try_metric_category_browse(query, part, category_match)
    if metric_category:
        return metric_category

    if category_match.method in {"default", "unclassified"}:
        return VendorLink(
            url="",
            link_kind="site_search",
            tier="not_applicable",
            category_id=category_match.category.id or "unclassified",
            category_label=category_match.category.label or "Unclassified",
            method="unclassified",
            confidence_hint=0.0,
        )

    return VendorLink(
        url=category_search_url(category_match.category.route, query),
        link_kind="category_search",
        tier="category_search",
        category_id=category_match.category.id,
        category_label=category_match.category.label,
        method=category_match.method,
        confidence_hint=0.55,
    )


def vendor_link_to_handler_link(link: VendorLink) -> McMasterLink:
    """Bridge to legacy `McMasterLink` consumed by matcher + tests."""
    link_type = link.link_kind
    return McMasterLink(
        url=link.url,
        link_type=link_type,  # type: ignore[arg-type]
        category_id=link.category_id,
        category_label=link.category_label,
        part_number=link.part_number,
        method=link.method,
    )


def vendor_link_from_context(ctx: VendorMatchContext) -> VendorLink:
    hit = None
    if ctx.catalog_part_number:
        hit = catalog_lookup(ctx.query)
    elif not ctx.catalog_part_number:
        hit = catalog_lookup(ctx.query)
    return resolve_mcmaster_link(ctx.query, part=ctx.part, catalog_hit=hit)
