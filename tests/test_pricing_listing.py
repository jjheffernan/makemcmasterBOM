"""Tests for McMaster listing price extraction."""

from backend.models.part import Part
from backend.services.pricing_listing import (
    apply_browse_row_pricing,
    parse_money,
    parse_quantity,
    pricing_from_api_breaks,
    pricing_from_browse_row,
    sync_parts_pricing_from_listings,
)
from backend.services.vendors.mcmaster.browse_parse import BrowseRow


def test_parse_money_strips_currency():
    assert parse_money("$12.34") == 12.34
    assert parse_money("1,234.50") == 1234.5


def test_parse_quantity_from_text():
    assert parse_quantity("100") == 100.0
    assert parse_quantity("Pkg of 50") == 50.0


def test_pricing_from_browse_row_pack():
    row = BrowseRow(
        part_number="91290A115",
        fields={"Price": "$0.12", "Pkg. Qty.": "100"},
    )
    listing = pricing_from_browse_row(row, bom_qty=4)
    assert listing is not None
    assert listing.price_min_qty == 100.0
    assert listing.price_batch_cost == 12.0
    assert listing.unit_cost is None
    assert listing.price_source == "listing"


def test_pricing_from_browse_row_each():
    row = BrowseRow(
        part_number="1234K52",
        fields={"Price": "$3.25"},
    )
    listing = pricing_from_browse_row(row, bom_qty=2)
    assert listing is not None
    assert listing.price_min_qty == 1.0
    assert listing.unit_cost == 3.25
    assert listing.price_batch_cost is None


def test_apply_browse_row_pricing_updates_part():
    part = Part(
        original_name="M3 screw",
        quantity=10,
        mcmaster_part_number="91290A115",
    )
    row = BrowseRow(
        part_number="91290A115",
        fields={"Price": "$0.10", "Pkg. Qty.": "50"},
    )
    updated = apply_browse_row_pricing(part, row)
    assert updated.price_min_qty == 50.0
    assert updated.price_batch_cost == 5.0
    assert updated.price_source == "listing"
    assert "91290A115" in updated.price_listing_note


def test_pricing_from_api_breaks_picks_tier():
    breaks = [
        {"MinimumQuantity": 1, "Amount": 1.0},
        {"MinimumQuantity": 100, "Amount": 0.8},
    ]
    listing = pricing_from_api_breaks(breaks, bom_qty=150, part_number="91290A120")
    assert listing is not None
    assert listing.price_min_qty == 100.0
    assert listing.price_batch_cost == 80.0
    assert listing.price_source == "api"


async def test_sync_skips_manual_parts():
    manual = Part(
        original_name="Custom",
        quantity=1,
        price_source="manual",
        unit_cost=9.99,
    )
    updated = await sync_parts_pricing_from_listings([manual])
    assert updated[0].price_source == "manual"
    assert updated[0].unit_cost == 9.99
