"""Extract McMaster listing prices from browse tables and official API breaks."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from backend.models.part import Part
from backend.services.vendors.mcmaster.browse_parse import BrowseRow, find_row_by_part_number
from backend.services.vendors.mcmaster.urls import mcmaster_product_url

logger = logging.getLogger(__name__)

PRICE_FIELD_KEYS = ("Price", "Each", "Unit Price")
PACK_QTY_FIELD_KEYS = (
    "Pkg. Qty.",
    "Pkg Qty",
    "Package Qty.",
    "Package Quantity",
    "Min. Order Qty.",
    "Minimum Order Qty.",
)


@dataclass(frozen=True)
class ListingPricing:
    price_min_qty: float
    price_batch_cost: float | None
    unit_cost: float | None
    price_source: str
    price_listing_note: str


def parse_money(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value >= 0 else None
    text = str(value).strip().replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_quantity(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    text = str(value).strip().lower()
    match = re.search(r"([\d.]+)", text.replace(",", ""))
    if not match:
        return None
    try:
        qty = float(match.group(1))
        return qty if qty > 0 else None
    except ValueError:
        return None


def _first_field(fields: dict[str, str | float], keys: tuple[str, ...]) -> str | float | None:
    for key in keys:
        if key in fields and fields[key] not in ("", None):
            return fields[key]
    lowered = {str(k).lower(): v for k, v in fields.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return value
    return None


def pricing_from_browse_row(row: BrowseRow, *, bom_qty: float) -> ListingPricing | None:
    """Map McMaster ProductPresentations row fields to batch/unit pricing."""
    price_raw = _first_field(row.fields, PRICE_FIELD_KEYS)
    unit_price = parse_money(price_raw)
    if unit_price is None:
        return None

    pack_raw = _first_field(row.fields, PACK_QTY_FIELD_KEYS)
    pack_qty = parse_quantity(pack_raw) or 1.0

    if pack_qty > 1:
        batch_cost = round(unit_price * pack_qty, 4)
        note = f"Listing {row.part_number}: ${unit_price:.4f}/ea × {int(pack_qty)} pack"
        return ListingPricing(
            price_min_qty=pack_qty,
            price_batch_cost=batch_cost,
            unit_cost=None,
            price_source="listing",
            price_listing_note=note,
        )

    return ListingPricing(
        price_min_qty=1.0,
        price_batch_cost=None,
        unit_cost=unit_price,
        price_source="listing",
        price_listing_note=f"Listing {row.part_number}: ${unit_price:.4f}/ea",
    )


def pricing_from_api_breaks(
    breaks: list[dict[str, Any]],
    *,
    bom_qty: float,
    part_number: str,
) -> ListingPricing | None:
    """Pick the best API price tier for the BOM quantity."""
    tiers: list[tuple[float, float]] = []
    for item in breaks:
        min_qty = parse_quantity(
            item.get("MinimumQuantity")
            or item.get("MinimumQty")
            or item.get("MinQty")
            or item.get("Quantity")
            or item.get("Qty")
            or 1
        )
        amount = parse_money(
            item.get("Amount")
            or item.get("Price")
            or item.get("UnitPrice")
            or item.get("UnitPriceAmount")
        )
        if min_qty and amount is not None:
            tiers.append((min_qty, amount))

    if not tiers:
        return None

    tiers.sort(key=lambda pair: pair[0])
    applicable = tiers[0]
    for min_qty, amount in tiers:
        if bom_qty >= min_qty:
            applicable = (min_qty, amount)

    min_qty, unit_price = applicable
    if min_qty > 1:
        return ListingPricing(
            price_min_qty=min_qty,
            price_batch_cost=round(unit_price * min_qty, 4),
            unit_cost=None,
            price_source="api",
            price_listing_note=f"API {part_number}: ${unit_price:.4f}/ea from qty {int(min_qty)}+",
        )
    return ListingPricing(
        price_min_qty=1.0,
        price_batch_cost=None,
        unit_cost=unit_price,
        price_source="api",
        price_listing_note=f"API {part_number}: ${unit_price:.4f}/ea",
    )


def apply_listing_pricing(part: Part, listing: ListingPricing) -> Part:
    return part.model_copy(
        update={
            "price_min_qty": listing.price_min_qty,
            "price_batch_cost": listing.price_batch_cost,
            "unit_cost": listing.unit_cost,
            "price_source": listing.price_source,
            "price_listing_note": listing.price_listing_note,
        }
    )


def apply_browse_row_pricing(part: Part, row: BrowseRow) -> Part:
    listing = pricing_from_browse_row(row, bom_qty=float(part.quantity or 0))
    if not listing:
        return part
    return apply_listing_pricing(part, listing)


def effective_unit_cost_for_row(row: BrowseRow, *, bom_qty: float) -> float | None:
    """Compare unit economics across browse table rows (pack-aware)."""
    from backend.services.pricing import compute_line_pricing

    listing = pricing_from_browse_row(row, bom_qty=bom_qty)
    if not listing:
        return None
    snapshot = Part(
        quantity=bom_qty,
        price_min_qty=listing.price_min_qty,
        price_batch_cost=listing.price_batch_cost,
        unit_cost=listing.unit_cost,
    )
    pricing = compute_line_pricing(snapshot)
    return pricing.unit_cost


async def fetch_listing_row_for_part(part: Part) -> BrowseRow | None:
    """Load product table row for a catalog part number (live browse)."""
    part_number = part.mcmaster_part_number.strip()
    if not part_number:
        return None

    from backend import config
    from backend.services.vendors.mcmaster.browse_fetch import fetch_browse_rows

    if not config.MCMASTER_BROWSE_RESOLVE_ENABLED:
        return None

    url = part.mcmaster_url or mcmaster_product_url(
        part_number,
        part.normalized_name or part.original_name,
    )
    try:
        rows = await fetch_browse_rows(url)
    except Exception as exc:
        logger.debug("Listing price fetch failed for %s: %s", part_number, exc)
        return None

    if not rows:
        return None
    match = find_row_by_part_number(rows, part_number)
    if match:
        return match

    from backend.services.vendors.mcmaster.browse_row_select import pick_lowest_price_row

    return pick_lowest_price_row(part, rows, browse_url=url)


def part_needs_pricing_sync(part: Part) -> bool:
    """Return True when a part still needs a live pricing fetch."""
    if part.mcmaster_status == "not_applicable":
        return False
    if part.price_source == "manual":
        return False
    if part.price_source in {"listing", "api"} and (
        part.unit_cost is not None or part.price_batch_cost is not None
    ):
        return False
    if not part.mcmaster_part_number and not part.mcmaster_url:
        return False
    return True


async def sync_part_pricing_from_listing(part: Part) -> Part:
    """Fill pricing fields from McMaster hardware listing (API, then live browse)."""
    if part.mcmaster_status == "not_applicable":
        return part
    if not part.mcmaster_part_number and not part.mcmaster_url:
        return part

    part_number = part.mcmaster_part_number.strip()
    bom_qty = float(part.quantity or 0)

    from backend.services.vendors.mcmaster.api import get_mcmaster_api_client

    client = get_mcmaster_api_client()
    if part_number and client.is_configured():
        try:
            breaks = await client.fetch_price(part_number)
            listing = pricing_from_api_breaks(breaks, bom_qty=bom_qty, part_number=part_number)
            if listing:
                return apply_listing_pricing(part, listing)
        except Exception as exc:
            logger.debug("API price fetch failed for %s: %s", part_number, exc)

    row = await fetch_listing_row_for_part(part)
    if row:
        return apply_browse_row_pricing(part, row)

    return part


async def sync_parts_pricing_from_listings(parts: list[Part]) -> list[Part]:
    updated: list[Part] = []
    for part in parts:
        if not part_needs_pricing_sync(part):
            updated.append(part)
        else:
            updated.append(await sync_part_pricing_from_listing(part))
    return updated
