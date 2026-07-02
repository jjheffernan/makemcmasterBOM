"""Tests for BOM batch / pack pricing."""

from backend.models.part import Part
from backend.services.pricing import compute_line_pricing, summarize_project_pricing


def test_unit_cost_from_batch_expression():
    part = Part(
        original_name="M3 screw",
        quantity=4,
        price_min_qty=100,
        price_batch_cost=12.0,
    )
    pricing = compute_line_pricing(part)
    assert pricing.unit_cost == 0.12
    assert "12.00 ÷ 100" in pricing.unit_cost_expression
    assert pricing.packs_ordered == 1
    assert pricing.order_qty == 100
    assert pricing.line_total == 12.0
    assert "1× pack" in pricing.batch_note


def test_multiple_packs_when_bom_exceeds_one_pack():
    part = Part(
        original_name="Washer",
        quantity=150,
        price_min_qty=100,
        price_batch_cost=8.5,
    )
    pricing = compute_line_pricing(part)
    assert pricing.packs_ordered == 2
    assert pricing.order_qty == 200
    assert pricing.line_total == 17.0


def test_manual_unit_cost_override():
    part = Part(
        original_name="Bearing",
        quantity=2,
        price_min_qty=1,
        unit_cost=3.25,
    )
    pricing = compute_line_pricing(part)
    assert pricing.unit_cost_override is True
    assert pricing.line_total == 6.5
    assert "manual" in pricing.unit_cost_expression


def test_per_unit_without_pack():
    part = Part(
        original_name="Bolt",
        quantity=10,
        price_min_qty=1,
        price_batch_cost=5.0,
    )
    pricing = compute_line_pricing(part)
    assert pricing.unit_cost == 5.0
    assert pricing.line_total == 50.0
    assert pricing.order_qty == 10


def test_summarize_project_pricing():
    parts = [
        Part(original_name="A", quantity=1, unit_cost=2.0),
        Part(original_name="B", quantity=1),
    ]
    summary = summarize_project_pricing(parts)
    assert summary["priced_lines"] == 1
    assert summary["project_total"] == 2.0
