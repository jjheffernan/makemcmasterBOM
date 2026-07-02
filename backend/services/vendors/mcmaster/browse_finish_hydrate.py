"""Hydrate finish variants and multi-row browse tables from live McMaster listings."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from backend import config
from backend.models.part import BrowseFinishOption, Part
from backend.services.pricing_listing import (
    apply_browse_row_pricing,
    effective_unit_cost_for_row,
    pricing_from_browse_row,
)
from backend.services.vendors.mcmaster.browse_fetch import fetch_browse_rows
from backend.services.vendors.mcmaster.browse_row_select import pick_lowest_price_row
from backend.services.vendors.mcmaster.filters import infer_finish_from_bom
from backend.services.vendors.mcmaster.finish_browse import (
    build_browse_finish_options,
    finish_option_for_id,
)
from backend.services.vendors.mcmaster.urls import mcmaster_product_url
from backend.services.vendors.mcmaster.hydration_session import HydrationSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _HydratedVariant:
    finish_id: str
    label: str
    browse_url: str
    row: object
    unit_cost: float | None
    option: BrowseFinishOption


def _resolve_policy(part: Part) -> str:
    if infer_finish_from_bom(part.normalized_name or part.original_name, part.specification):
        return "finish"
    policy = (part.match_selection_policy or "lowest_price").strip().lower()
    if policy in {"finish", "lowest_price"}:
        return policy
    return "lowest_price"


def _build_finish_option(
    finish_id: str,
    label: str,
    browse_url: str,
    row,
    part: Part,
) -> _HydratedVariant:
    bom_qty = float(part.quantity or 1)
    unit_cost = effective_unit_cost_for_row(row, bom_qty=bom_qty)
    listing = pricing_from_browse_row(row, bom_qty=bom_qty)
    product_url = mcmaster_product_url(
        row.part_number,
        part.normalized_name or part.original_name,
    )
    note = listing.price_listing_note if listing else ""
    option = BrowseFinishOption(
        finish_id=finish_id,
        label=label,
        mcmaster_url=browse_url,
        mcmaster_part_number=row.part_number,
        product_url=product_url,
        unit_cost=unit_cost,
        price_min_qty=listing.price_min_qty if listing else 1.0,
        price_batch_cost=listing.price_batch_cost if listing else None,
        price_listing_note=note,
    )
    return _HydratedVariant(
        finish_id=finish_id,
        label=label,
        browse_url=browse_url,
        row=row,
        unit_cost=unit_cost,
        option=option,
    )


async def _hydrate_single_url(
    part: Part,
    *,
    finish_id: str,
    label: str,
    browse_url: str,
    session: HydrationSession | None = None,
) -> _HydratedVariant | None:
    if session:
        cached = session.get_cached_option(browse_url, finish_id)
        if cached and cached.mcmaster_part_number:
            return _HydratedVariant(
                finish_id=finish_id,
                label=label,
                browse_url=browse_url,
                row=_CachedRow(cached),
                unit_cost=cached.unit_cost,
                option=cached,
            )

    try:
        rows = await fetch_browse_rows(browse_url)
    except Exception as exc:
        logger.debug("Finish hydrate failed for %s: %s", browse_url, exc)
        return None
    if not rows:
        return None

    row = pick_lowest_price_row(part, rows, browse_url=browse_url)
    if not row:
        return None
    variant = _build_finish_option(finish_id, label, browse_url, row, part)
    if session:
        session.store_option(browse_url, finish_id, variant.option)
    return variant


@dataclass(frozen=True)
class _CachedRow:
    """Minimal row stand-in when reusing a hydrated finish option."""

    option: BrowseFinishOption

    @property
    def part_number(self) -> str:
        return self.option.mcmaster_part_number


def _apply_variant(part: Part, variant: _HydratedVariant, *, policy: str) -> Part:
    reason = (
        f"Live McMaster table — {variant.row.part_number} "
        f"({variant.label}; {policy} selection"
    )
    if variant.unit_cost is not None:
        reason += f", ${variant.unit_cost:.4f}/ea"
    reason += ")"

    updated = part.model_copy(
        update={
            "mcmaster_part_number": variant.row.part_number,
            "mcmaster_url": variant.option.product_url or variant.browse_url,
            "selected_finish_id": variant.finish_id,
            "match_selection_policy": policy,
            "match_tier": "filtered_browse",
            "mcmaster_status": "likely",
            "confidence": max(part.confidence, 0.9),
            "mcmaster_reason": reason,
            "hardware_match_status": "verified",
        }
    )
    if isinstance(variant.row, _CachedRow):
        return updated.model_copy(
            update={
                "price_source": "listing",
                "price_listing_note": variant.option.price_listing_note,
                "price_min_qty": variant.option.price_min_qty,
                "price_batch_cost": variant.option.price_batch_cost,
                "unit_cost": variant.option.unit_cost,
            }
        )
    return apply_browse_row_pricing(updated, variant.row)


async def hydrate_part_from_browse(
    part: Part,
    *,
    session: HydrationSession | None = None,
) -> Part:
    """
    Load live McMaster product tables for finish variants (or the primary browse URL).

    Defaults to lowest unit cost when the BOM does not specify a finish.
    """
    if not config.MCMASTER_BROWSE_RESOLVE_ENABLED:
        return part
    if part.mcmaster_status == "not_applicable":
        return part

    from backend.services.vendors.mcmaster.hydration_session import (
        hydration_group_key,
        part_already_hydrated,
    )

    if part_already_hydrated(part):
        return part

    group_key = hydration_group_key(part)
    if session:
        template = session.get_group_template(group_key)
        if template:
            options, selected_finish_id = template
            chosen_option = finish_option_for_id(options, selected_finish_id)
            if chosen_option and chosen_option.mcmaster_part_number:
                policy = _resolve_policy(part)
                updates: dict[str, object] = {
                    "browse_finish_options": options,
                    "selected_finish_id": selected_finish_id,
                    "mcmaster_part_number": chosen_option.mcmaster_part_number,
                    "mcmaster_url": chosen_option.product_url or chosen_option.mcmaster_url,
                    "match_selection_policy": policy,
                    "price_source": "listing",
                    "price_listing_note": chosen_option.price_listing_note,
                    "price_min_qty": chosen_option.price_min_qty,
                    "price_batch_cost": chosen_option.price_batch_cost,
                    "unit_cost": chosen_option.unit_cost,
                }
                return part.model_copy(update=updates)

    policy = _resolve_policy(part)
    finish_options = list(part.browse_finish_options)

    if not finish_options and part.match_tier == "filtered_browse" and part.mcmaster_url:
        query = part.normalized_name or part.original_name
        rebuilt = build_browse_finish_options(
            query,
            part,
            category_id=part.mcmaster_category or "screw",
            filter_path=_filter_path_from_url(part.mcmaster_url),
        )
        finish_options = rebuilt

    variants: list[_HydratedVariant] = []

    if finish_options:
        tasks = [
            _hydrate_single_url(
                part,
                finish_id=option.finish_id,
                label=option.label,
                browse_url=option.mcmaster_url,
                session=session,
            )
            for option in finish_options
        ]
        results = await asyncio.gather(*tasks)
        variants = [result for result in results if result]
    elif part.mcmaster_url and part.match_tier in {"filtered_browse", "category_search"}:
        hydrated = await _hydrate_single_url(
            part,
            finish_id="default",
            label="Listing",
            browse_url=part.mcmaster_url,
            session=session,
        )
        if hydrated:
            variants.append(hydrated)

    if not variants:
        return part

    hydrated_options = [variant.option for variant in variants]

    if policy == "finish":
        target_finish = infer_finish_from_bom(
            part.normalized_name or part.original_name,
            part.specification,
        )
        chosen = next((v for v in variants if v.finish_id == target_finish), None)
        if chosen is None and part.selected_finish_id:
            chosen = next(
                (v for v in variants if v.finish_id == part.selected_finish_id),
                None,
            )
        if chosen is None:
            priced = [v for v in variants if v.unit_cost is not None]
            chosen = min(priced, key=lambda v: v.unit_cost) if priced else variants[0]
    else:
        priced = [v for v in variants if v.unit_cost is not None]
        if priced:
            chosen = min(priced, key=lambda v: v.unit_cost)
        else:
            chosen = variants[0]

    updated = _apply_variant(part, chosen, policy=policy)
    result = updated.model_copy(
        update={
            "browse_finish_options": hydrated_options,
            "selected_finish_id": chosen.finish_id,
        }
    )
    if session:
        session.store_group_template(group_key, hydrated_options, chosen.finish_id)
    return result


def apply_finish_selection(part: Part, finish_id: str) -> Part:
    """Apply a hydrated finish option without another network round-trip."""
    option = finish_option_for_id(part.browse_finish_options, finish_id)
    if not option or not option.mcmaster_part_number:
        if option:
            return part.model_copy(
                update={
                    "selected_finish_id": finish_id,
                    "mcmaster_url": option.product_url or option.mcmaster_url,
                    "match_selection_policy": "finish",
                }
            )
        return part

    updates: dict[str, object] = {
        "selected_finish_id": finish_id,
        "mcmaster_part_number": option.mcmaster_part_number,
        "mcmaster_url": option.product_url or option.mcmaster_url,
        "match_selection_policy": "finish",
        "price_source": "listing",
        "price_listing_note": option.price_listing_note,
        "price_min_qty": option.price_min_qty,
        "price_batch_cost": option.price_batch_cost,
        "unit_cost": option.unit_cost,
    }
    return part.model_copy(update=updates)


def _filter_path_from_url(url: str) -> str:
    marker = ".com"
    idx = url.lower().find(marker)
    if idx < 0:
        return ""
    path = url[idx + len(marker) :].split("?", 1)[0]
    if "/products/" not in path:
        return ""
    after_products = path.split("/products/", 1)[-1]
    segments = [segment for segment in after_products.split("/") if segment]
    filter_segments = [
        segment
        for segment in segments
        if segment.startswith(
            ("system-of-measurement", "thread-size", "length", "trade")
        )
    ]
    if not filter_segments:
        return ""
    return "".join(f"{segment}/" for segment in filter_segments)
