"""Tests for quantity parsing and runtime validation helpers."""

from pathlib import Path

from backend.services.description_bom import parse_bom_line, parts_from_description
from backend.services.parsers.helpers.bom_quantities import parse_quantity_and_name
from backend.services.parsers.helpers.quantity_checks import (
    check_part,
    check_parsed_line,
    check_parts,
)

FIXTURES = Path(__file__).parent / "fixtures"
MEGA_PYTHON_COLON_LINE = (
    "Left front side and left rear sides against first modules: 13 x M3-16 mm"
)


def test_colon_qty_hardware_splits_fields():
    qty, name, spec, context = parse_quantity_and_name(MEGA_PYTHON_COLON_LINE)
    assert qty == 13
    assert "m3-16" in name.lower()
    assert spec == ""
    assert "left front" in context.lower()


def test_colon_qty_hardware_parse_bom_line():
    part = parse_bom_line(MEGA_PYTHON_COLON_LINE)
    assert part is not None
    assert part.quantity == 13
    assert "m3-16" in part.original_name.lower()
    assert "left front" in part.notes.lower()
    assert not part.specification.startswith("13")


def test_summary_qty_leading_unchanged():
    qty, name, spec, context = parse_quantity_and_name("75 x M3-16 mm")
    assert qty == 75
    assert "m3-16" in name.lower()
    assert spec == ""
    assert context == ""


def test_name_colon_dimension_unchanged():
    qty, name, spec, context = parse_quantity_and_name("Whiteboard marker / Foil pen: 0.6mm")
    assert qty == 1
    assert "marker" in name.lower()
    assert "0.6mm" in spec
    assert context == ""


def test_name_colon_qty_product_not_split_assembly():
    """Product lines like 'Cards: 3 x 5 inch' keep the product name on the left."""
    qty, name, spec, context = parse_quantity_and_name(
        "Rewriteable Cards: 3 x 5 inch / 76mm x 127mm"
    )
    assert qty == 1
    assert "card" in name.lower()
    assert "5 inch" in spec or "76mm" in spec
    assert context == ""


def test_pcs_leading_line():
    qty, name, spec, context = parse_quantity_and_name("150 pcs M3 Hex Socket Head Kit")
    assert qty == 150
    assert "m3" in name.lower()


def test_check_parsed_line_ok_for_colon_hardware():
    assert check_parsed_line(MEGA_PYTHON_COLON_LINE) == []


def test_check_part_flags_qty_in_specification():
    from backend.models.part import Part

    part = Part(
        quantity=1,
        original_name="Left front side against modules",
        specification="13 x M3-16 mm",
        notes="MakerWorld BOM (description)",
    )
    issues = check_part(part)
    assert any(i.code == "qty_in_specification" for i in issues)
    assert any(i.code == "hardware_in_specification" for i in issues)


def test_mega_python_fixture_quantity_checks():
    text = (FIXTURES / "description_mega_python.txt").read_text()
    parts = parts_from_description(text)
    issues = check_parts(parts)
    assert not any(i.code == "qty_in_specification" for i in issues)
    assert not any(i.code == "hardware_in_specification" for i in issues)

    m3_16 = [p for p in parts if "m3-16" in p.original_name.lower()]
    assert any(p.quantity == 75 for p in m3_16)
    assert any(p.quantity == 13 for p in m3_16)
