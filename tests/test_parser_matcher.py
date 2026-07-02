import pytest

from backend.models.part import Part
from backend.services.matcher import (
    classify_mcmaster_eligibility,
    match_part,
    match_parts,
    summarize_mcmaster_coverage,
)
from backend.services.parser import parse_bom_bytes
from backend.services.pipeline import import_from_file


SAMPLE_CSV = b"""Qty,Part Name,Specification
4,M3x8 Socket Head Cap Screw,Stainless Steel
2,608ZZ Ball Bearing,8x22x7
"""


def test_parse_bom_csv():
    parts = parse_bom_bytes(SAMPLE_CSV, "bom.csv")
    assert len(parts) == 2
    assert parts[0].original_name == "M3x8 Socket Head Cap Screw"
    assert parts[0].quantity == 4


def test_matcher_generates_url_for_hardware():
    part = Part(original_name="M3 screw", specification="stainless")
    matched = match_part(part)
    assert "mcmaster.com" in matched.mcmaster_url
    assert matched.confidence > 0
    assert matched.mcmaster_status in {"likely", "possible"}


def test_printed_part_not_applicable():
    part = Part(original_name="Body Cover", specification="3D printed PETG")
    matched = match_part(part)
    assert matched.mcmaster_status == "not_applicable"
    assert matched.mcmaster_url == ""
    assert matched.confidence == 0.0
    assert "3D-printed" in matched.mcmaster_reason


def test_electronics_not_applicable():
    part = Part(original_name="Arduino Nano", specification="")
    matched = match_part(part)
    assert matched.mcmaster_status == "not_applicable"
    assert matched.mcmaster_url == ""
    assert "Electronics" in matched.mcmaster_reason


def test_match_reason_copied_to_notes():
    part = Part(
        original_name="M3x8 Socket Head Cap Screw",
        specification="Stainless Steel",
        notes="MakerWorld BOM (description)",
    )
    matched = match_part(part)
    assert matched.mcmaster_reason
    assert "MakerWorld BOM (description)" in matched.notes
    assert "McMaster (" in matched.notes
    assert matched.mcmaster_reason in matched.notes


def test_not_applicable_reason_in_notes():
    part = Part(original_name="Body Cover", specification="3D printed PETG")
    matched = match_part(part)
    assert "3D-printed" in matched.mcmaster_reason
    assert "McMaster (not applicable):" in matched.notes
    assert "3D-printed" in matched.notes


def test_custom_part_without_category_match_is_not_applicable():
    part = Part(original_name="Enclosure lid", specification="")
    matched = match_part(part)
    assert matched.mcmaster_status == "not_applicable"
    assert matched.mcmaster_url == ""
    assert matched.match_tier == "not_applicable"


def test_classify_empty_part():
    status, reason = classify_mcmaster_eligibility(Part(original_name=""))
    assert status == "not_applicable"
    assert reason


def test_import_from_file_csv():
    content = b"Qty,Part Name\n1,M3 screw\n"
    import asyncio

    project = asyncio.run(import_from_file(content, "bom.csv"))
    assert len(project.parts) == 1
    assert project.title


def test_summarize_coverage():
    parts = match_parts(
        [
            Part(original_name="M3 bolt"),
            Part(original_name="PLA printed spacer"),
            Part(original_name="Widget mount"),
        ]
    )
    summary = summarize_mcmaster_coverage(parts)
    assert summary["not_applicable"] >= 1
    assert sum(summary.values()) == 3


@pytest.mark.parametrize(
    ("name", "spec", "expect_status", "expect_in_query"),
    [
        ("M3x8 SHCS", "Maker's Supply", "likely", "socket head cap screw"),
        ("M3x8", "Maker's Supply", "likely", "M3x8 screw"),
        ("M4x10 BHCS (10PCS) - B-KA007", "", "likely", "button head cap screw"),
        ("DIN912 M3x8", "", "likely", "socket head cap screw"),
        ("#6-32 x 1/2\"", "", "possible", "screw"),
        ("M3 Hex Nut", "Stainless Steel", "likely", "nut"),
    ],
)
def test_bolt_and_fastener_patterns(name, spec, expect_status, expect_in_query):
    matched = match_part(Part(original_name=name, specification=spec))
    assert matched.mcmaster_status == expect_status
    assert expect_in_query.lower() in matched.normalized_name.lower()
    assert "maker" not in matched.normalized_name.lower()
    assert matched.mcmaster_url
    min_confidence = 0.4 if expect_status == "possible" else 0.7
    assert matched.confidence >= min_confidence


def test_kumiko_embedded_bom_keeps_all_parts_with_na_links():
    import json
    from pathlib import Path

    from backend.services.makerworld_bom import parts_from_design
    from backend.services.matcher import match_parts

    design = json.loads(
        (Path(__file__).parent / "fixtures" / "makerworld_kumiko_design.json").read_text()
    )
    matched = match_parts(parts_from_design(design))
    assert len(matched) == 4
    by_name = {p.original_name: p for p in matched}
    assert by_name["LED Lamp Kit (1pcs) - MH001"].mcmaster_status == "not_applicable"
    assert by_name["LED Lamp Kit (1pcs) - MH001"].mcmaster_url == ""
    assert by_name["Matte Charcoal (11101) / Refill / 1kg"].mcmaster_status == "not_applicable"
    assert by_name["Matte Charcoal (11101) / Refill / 1kg"].mcmaster_url == ""
    assert by_name["led-light-bulb-low-lumen"].mcmaster_url == ""


def test_csv_export_includes_not_applicable_parts():
    from backend.services.pipeline import parts_to_csv

    parts = match_parts(
        [
            Part(original_name="M3 bolt", specification=""),
            Part(original_name="PLA printed spacer", specification="3D printed"),
        ]
    )
    csv_text = parts_to_csv(parts)
    assert "M3 bolt" in csv_text
    assert "PLA printed spacer" in csv_text
    assert csv_text.count("\n") >= 3  # header + 2 rows


def test_merge_file_and_embedded_parts():
    from backend.services.description_bom import merge_parts

    file_parts = [
        Part(original_name="M3x8 screw", quantity=4, mcmaster_url="https://example.com"),
    ]
    embedded = [
        Part(original_name="PLA filament", quantity=1, notes="MakerWorld BOM (filament)"),
        Part(original_name="M3x8 screw", quantity=4),
    ]
    merged = merge_parts(file_parts, embedded)
    assert len(merged) == 2
    assert merged[0].original_name == "M3x8 screw"
    assert merged[1].original_name == "PLA filament"


def test_normalize_strips_makerworld_category():
    from backend.services.matcher import normalize_hardware_name

    assert normalize_hardware_name("M3x8 SHCS", "Maker's Supply") == (
        "M3x8 socket head cap screw"
    )


def test_filament_via_notes_not_applicable():
    part = Part(
        original_name="Matte Charcoal (11101) / Refill / 1kg",
        notes="MakerWorld BOM (filament)",
    )
    matched = match_part(part)
    assert matched.mcmaster_status == "not_applicable"
    assert matched.mcmaster_url == ""
