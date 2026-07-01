"""Tests for specification metadata normalization and validation."""

from backend.models.part import Part
from backend.services.parsers.helpers.spec_metadata import (
    classify_hardware_kind,
    normalize_part_specification,
    normalize_specification_text,
    spec_field_hint,
)
from backend.services.parsers.helpers.specification_checks import check_part_specification


def test_classify_fastener_and_bearing():
    assert classify_hardware_kind("M3-16 mm socket head cap screw") == "fastener"
    assert classify_hardware_kind("608ZZ bearing") == "bearing"


def test_spec_hint_for_fastener():
    part = Part(original_name="M4 screw")
    assert "head" in spec_field_hint(part).lower()


def test_normalize_strips_duplicate_metric_from_spec():
    name, spec, notes = normalize_specification_text(
        "M3-16 mm socket head cap screw",
        "M3-16 mm stainless",
        "",
    )
    assert "m3" not in spec.lower() or "stainless" in spec.lower()
    assert "socket" not in spec.lower()


def test_normalize_moves_assembly_prose_to_notes():
    part = normalize_part_specification(
        Part(
            original_name="Module bracket",
            specification="Left front side against first modules: 13 x M3-16 mm",
            notes="",
        )
    )
    assert part.specification == ""
    assert "left front" in part.notes.lower()


def test_check_flags_identity_in_specification():
    part = Part(
        original_name="M3-25 mm",
        specification="13 x M3-16 mm",
        notes="",
    )
    codes = {i.code for i in check_part_specification(part)}
    assert codes & {
        "size_in_specification",
        "identity_in_specification",
        "qty_in_specification",
        "quantity_in_specification",
    }


def test_check_warns_missing_bearing_shield():
    part = Part(original_name="608 bearing", specification="")
    codes = {i.code for i in check_part_specification(part)}
    assert "missing_bearing_shield" in codes


def test_check_accepts_socket_in_name_with_finish_in_spec():
    part = Part(
        original_name="M3-16 mm socket head cap screw",
        specification="18-8 stainless, fully threaded",
    )
    errors = [i for i in check_part_specification(part) if i.severity == "error"]
    assert not errors


def test_check_accepts_bearing_with_zz_in_name():
    part = Part(original_name="608-ZZ bearing", specification="")
    warnings = [i for i in check_part_specification(part) if i.code == "missing_bearing_shield"]
    assert not warnings
