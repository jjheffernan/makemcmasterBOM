"""Tests for non-searchable BOM line detection."""

import pytest

from backend.models.part import Part
from backend.services.matcher import match_part
from backend.services.searchability import analyze_searchability


@pytest.mark.parametrize(
    ("name", "spec", "category"),
    [
        ("See assembly diagram for hardware", "", "instruction"),
        ("Please use M3 screws as needed", "", "instruction"),
        ("https://example.com/part", "", "markup"),
        ("**Bold note about fasteners**", "", "markup"),
        ("TBD", "", "placeholder"),
        ("---", "", "placeholder"),
        ("What size screw do I need?", "", "natural_language"),
        (
            "This line is a long assembly note without any real hardware designation",
            "",
            "natural_language",
        ),
        ("enclosure_body.stl", "", "file_reference"),
    ],
)
def test_non_searchable_lines(name, spec, category):
    result = analyze_searchability(name, spec)
    assert not result.searchable
    assert result.category == category


@pytest.mark.parametrize(
    "name",
    [
        "M3x8 socket head cap screw",
        "M3 Nut",
        "608-ZZ bearing",
        "91290A110",
    ],
)
def test_searchable_hardware(name):
    assert analyze_searchability(name).searchable


def test_match_part_skips_instruction_line():
    matched = match_part(
        Part(original_name="See diagram above for bolt sizes", specification="")
    )
    assert matched.mcmaster_status == "not_applicable"
    assert matched.mcmaster_url == ""
    assert matched.match_tier == "not_applicable"


def test_match_part_no_standard_components_search():
    matched = match_part(Part(original_name="widget bracket", specification="aluminum"))
    assert matched.mcmaster_status == "not_applicable"
    assert "standard-components" not in matched.mcmaster_url
    assert matched.match_tier == "not_applicable"
