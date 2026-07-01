"""Tests for hardware size/length extraction and post-match verification."""

import pytest

from backend.models.part import Part
from backend.services.hardware_match_verify import (
    check_length,
    check_size,
    correct_hardware_match,
    verify_hardware_match,
)
from backend.services.hardware_spec import (
    MetricFastenerSpec,
    extract_fastener_specs,
    primary_fastener_spec,
    spec_from_catalog_hit,
)
from backend.services.matcher import build_search_query, match_part
from backend.services.mcmaster_catalog import catalog_lookup
from backend.services.mcmaster_handler import build_mcmaster_link


@pytest.mark.parametrize(
    ("text", "diameter", "length"),
    [
        ("M3-16 mm", 3, 16),
        ("M3x25 screw", 3, 25),
        ("M3-25 mm socket head", 3, 25),
        ("M4 screws 40mm", 4, 40),
        ("M4 screw 40 mm", 4, 40),
        ("13 x M3-16 mm", 3, 16),
    ],
)
def test_extract_fastener_length(text, diameter, length):
    spec = extract_fastener_specs(text)[0]
    assert spec.diameter_mm == diameter
    assert spec.length_mm == length


def test_primary_spec_prefers_original_name():
    part = Part(original_name="M3-25 mm", specification="13 x M3-16 mm")
    spec = primary_fastener_spec(part)
    assert spec is not None
    assert spec.diameter_mm == 3
    assert spec.length_mm == 25


def test_build_search_query_ignores_conflicting_specification():
    part = Part(original_name="M3-25 mm", specification="13 x M3-16 mm")
    query = build_search_query(part)
    assert "M3x25" in query.replace(" ", "")
    assert "M3x16" not in query.replace(" ", "")


def test_match_part_verifies_m3_25_length():
    matched = match_part(Part(original_name="M3-25 mm"))
    assert matched.match_tier == "filtered_browse"
    assert matched.confidence == 0.90
    assert matched.hardware_length_mm == 25
    assert matched.hardware_diameter_mm == 3
    catalog_alt = next(
        (a for a in matched.match_alternatives if a.mcmaster_part_number == "91290A115"),
        None,
    )
    assert catalog_alt is not None
    assert catalog_alt.match_tier == "rule"


def test_match_part_detects_length_mismatch_when_wrong_catalog_forced():
    part = Part(original_name="M3-25 mm")
    wrong_hit = catalog_lookup("M3x16 mm socket head cap screw")
    link = build_mcmaster_link("M3x16 mm socket head cap screw", catalog_hit=wrong_hit)
    check = verify_hardware_match(part, hit=wrong_hit)
    assert check.status == "length_mismatch"
    assert check.expected and check.expected.length_mm == 25
    assert check.matched and check.matched.length_mm == 16

    _, _, corrected = correct_hardware_match(
        part,
        query="M3x16 mm socket head cap screw",
        hit=wrong_hit,
        link=link,
        check=check,
    )
    assert corrected.status == "corrected"
    assert corrected.matched and corrected.matched.length_mm == 25


def test_check_size_mismatch():
    expected = MetricFastenerSpec(diameter_mm=3, length_mm=25)
    matched = MetricFastenerSpec(diameter_mm=4, length_mm=25)
    part = Part(original_name="M3-25 mm")
    issue = check_size(part, matched)
    assert issue is not None
    assert issue.status == "size_mismatch"


def test_check_length_mismatch():
    expected = MetricFastenerSpec(diameter_mm=3, length_mm=25)
    matched = MetricFastenerSpec(diameter_mm=3, length_mm=16)
    part = Part(original_name="M3-25 mm")
    issue = check_length(part, matched)
    assert issue is not None
    assert issue.status == "length_mismatch"


def test_spec_from_catalog_hit_m3_series():
    hit = catalog_lookup("M3x16 socket head cap screw")
    assert hit is not None
    spec = spec_from_catalog_hit(hit)
    assert spec is not None
    assert spec.diameter_mm == 3
    assert spec.length_mm == 16
