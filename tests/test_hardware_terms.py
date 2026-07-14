"""Tests for shared hardware keyword and pattern library."""

import pytest

from backend.services.hardware_terms import (
    METRIC_SIZES,
    extract_metric_sizes,
    has_axial_dimension,
    has_fastener_prefix,
    has_fastener_suffix,
    has_fastener_type,
    has_hardware_signal,
    has_length_mm,
    has_metric_fastener,
    has_metric_size,
)


@pytest.mark.parametrize(
    "text",
    ["M3", "M2.5", "M12", "m4 bolt", "M10 washer"],
)
def test_has_metric_size_labels(text):
    assert has_metric_size(text)


@pytest.mark.parametrize(
    "text",
    [
        "M3x8 socket head",
        "M4*12mm",
        "M3-16 mm",
        "M2.5×6",
    ],
)
def test_has_metric_fastener_forms(text):
    assert has_metric_fastener(text)


@pytest.mark.parametrize("size", METRIC_SIZES)
def test_extract_metric_sizes_includes_catalog(size):
    assert size in extract_metric_sizes(f"need {size} and {size}x8")


@pytest.mark.parametrize(
    "text",
    [
        "hex bolt",
        "hex bolts",
        "socket head cap screw",
        "M3 screws",
        "M3 nut",
        "flat washer",
    ],
)
def test_has_fastener_type_and_suffix(text):
    assert has_fastener_type(text)
    assert has_fastener_suffix(text)


@pytest.mark.parametrize(
    "text",
    ["socket head cap screw", "hex bolt", "button head", "allen cap"],
)
def test_has_fastener_prefix(text):
    assert has_fastener_prefix(text)


@pytest.mark.parametrize(
    "text",
    [
        "5x30",
        "5×30mm",
        "8x22x7",
        "12/10mm",
        "Tubes 25/23mm",
    ],
)
def test_has_axial_dimension_patterns(text):
    assert has_axial_dimension(text)


@pytest.mark.parametrize(
    "text",
    ["30mm", "30 mm", "1.5mm", "16 mm screw"],
)
def test_has_length_mm(text):
    assert has_length_mm(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("M3-16 mm socket head screw", True),
        ("75 x M3-16 mm", True),
        ("608-ZZ bearings", True),
        ("5x30 magnet", True),
        ("Whiteboard marker", True),
        ("Intro paragraph about the project", False),
        ("Personalization settings", False),
    ],
)
def test_has_hardware_signal(text, expected):
    assert has_hardware_signal(text) is expected
