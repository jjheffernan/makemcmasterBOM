"""Tests for rule-based description BOM extraction."""

from pathlib import Path

import pytest

from backend.services.description_bom import (
    find_bom_section_lines,
    html_to_text,
    merge_description_with_embedded,
    parse_description_bom,
    parts_from_description,
    parse_bom_line,
)
from backend.models.part import Part
from backend.services.matcher import match_parts

FIXTURES = Path(__file__).parent / "fixtures"


def test_html_to_text_strips_tags():
    html = "<p>Hello <strong>world</strong></p>"
    assert "Hello" in html_to_text(html) and "world" in html_to_text(html)


def test_find_material_required_section():
    html = (FIXTURES / "description_material_required.html").read_text()
    text = html_to_text(html)
    lines = find_bom_section_lines(text)
    assert any("magnet" in line.lower() for line in lines)
    assert any("marker" in line.lower() for line in lines)
    assert not any("nozzle" in line.lower() for line in lines)


def test_parse_quantity_leading():
    part = parse_bom_line("4x 5mm magnets", require_hardware_keyword=False)
    assert part is not None
    assert part.quantity == 4
    assert "magnet" in part.original_name.lower()


def test_parse_name_colon_spec():
    part = parse_bom_line(
        "Whiteboard marker / Foil pen: 0.6mm",
        require_hardware_keyword=False,
    )
    assert part is not None
    assert "marker" in part.original_name.lower()
    assert "0.6mm" in part.specification


def test_parts_from_description_fixture():
    html = (FIXTURES / "description_material_required.html").read_text()
    parts = parts_from_description(html)
    names = [p.original_name.lower() for p in parts]
    assert any("magnet" in n for n in names)
    assert any("marker" in n for n in names)
    assert any("card" in n for n in names)
    assert all(p.notes == "MakerWorld BOM (description)" for p in parts)


def test_description_parts_get_matched_in_pipeline():
    html = (FIXTURES / "description_material_required.html").read_text()
    parts = match_parts(parts_from_description(html))
    assert len(parts) >= 3
    magnets = next(p for p in parts if "magnet" in p.original_name.lower())
    assert magnets.quantity == 4


def test_bom_section_header_variants():
    text = "Hardware needed\nM3x8 screw\nM3 washer"
    parts = parts_from_description(text)
    assert len(parts) == 2


def test_mega_python_description_bom():
    text = (FIXTURES / "description_mega_python.txt").read_text()
    parts = parts_from_description(text)
    names = " ".join(p.original_name.lower() for p in parts)
    assert len(parts) >= 10
    assert "m3" in names
    assert "bearing" in names
    assert "ptfe" in names
    m3_16 = [p for p in parts if "m3-16" in p.original_name.lower()]
    assert m3_16
    assert any(p.quantity == 75 for p in m3_16)
    assert any(p.quantity == 13 for p in m3_16)
    m3_12 = [p for p in parts if "m3-12" in p.original_name.lower()]
    assert m3_12
    assert any(p.quantity == 6 for p in m3_12)
    assert any(p.quantity == 4 for p in m3_12)


def test_description_summary_truncates_long_intro():
    from backend.services.description_bom import description_summary

    text = (FIXTURES / "description_mega_python.txt").read_text()
    summary = description_summary("Intro text about Mega Python.\n\n" + text)
    assert "M3-16" not in summary
    assert "75 x" not in summary
    assert "Intro" in summary


def test_normalize_prose_runons():
    from backend.services.description_bom import normalize_prose

    assert "Parts:" in normalize_prose("joint.Parts:M4 screws")
    assert "screws 40mm" in normalize_prose("M4 screws40mm: 21pcs")


@pytest.mark.parametrize(
    "line",
    [
        "BOM:",
        "Bill of Materials",
        "Shopping list",
        "You will need",
    ],
)
def test_section_starters(line):
    text = f"{line}\n4x M3x8 socket head cap screw\nSettings\n0.4mm nozzle"
    parts = parts_from_description(text)
    assert len(parts) == 1
    assert "screw" in parts[0].original_name.lower()


def test_parse_description_bom_explicit_flag():
    explicit = parse_description_bom("Bill of Materials\n4x M3x8 socket head cap screw")
    assert explicit.from_explicit_section
    assert len(explicit.parts) == 1

    fallback = parse_description_bom("This design uses M3x8 socket head cap screws throughout.")
    assert not fallback.from_explicit_section


def test_inline_bill_of_materials_header():
    text = "Build notes. Bill of Materials: 4x M3x8 socket head cap screw"
    parts = parts_from_description(text)
    assert len(parts) == 1
    assert "screw" in parts[0].original_name.lower()


def test_explicit_description_wins_merge_over_embedded():
    description = [
        Part(
            original_name="M3x8 socket head cap screw, black oxide",
            quantity=12,
            notes="MakerWorld BOM (description)",
        ),
    ]
    embedded = [
        Part(
            original_name="M3x8 socket head cap screw",
            quantity=12,
            notes="MakerWorld BOM (embedded)",
        ),
        Part(original_name="PLA filament", quantity=1, notes="MakerWorld BOM (filament)"),
    ]
    merged = merge_description_with_embedded(
        embedded,
        description,
        description_explicit=True,
    )
    assert merged[0].original_name == description[0].original_name
    assert merged[0].notes == "MakerWorld BOM (description)"
    assert any(p.original_name == "PLA filament" for p in merged)


def test_inferred_description_loses_merge_to_embedded():
    description = [
        Part(
            original_name="M3x8 socket head cap screw",
            quantity=4,
            notes="MakerWorld BOM (description)",
        ),
    ]
    embedded = [
        Part(
            original_name="M3x8 socket head cap screw",
            quantity=4,
            notes="MakerWorld BOM (embedded)",
        ),
    ]
    merged = merge_description_with_embedded(
        embedded,
        description,
        description_explicit=False,
    )
    assert merged[0].notes == "MakerWorld BOM (embedded)"


def test_runon_bill_of_materials_bom_parenthetical():
    text = (FIXTURES / "description_openmanet_bom.txt").read_text()
    result = parse_description_bom(text)
    assert result.from_explicit_section
    names = " ".join(p.original_name.lower() for p in result.parts)
    assert len(result.parts) >= 10
    assert "raspberry pi" in names
    assert "m3 screw" in names
    assert "m2.5 screw" in names
    assert "heat set" in names
    assert not any(p.original_name.lower() == "https" for p in result.parts)
    screws = [p for p in result.parts if "m3 screw" in p.original_name.lower()]
    assert screws and screws[0].quantity == 14

    matched = match_parts(result.parts)
    m3_screws = next(p for p in matched if "m3 screw" in p.original_name.lower())
    assert m3_screws.mcmaster_url
    assert m3_screws.match_tier in {"filtered_browse", "category_search", "catalog", "rule"}
