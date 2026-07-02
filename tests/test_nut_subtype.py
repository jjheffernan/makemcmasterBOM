"""Unit tests for nut family routing."""

from backend.services.vendors.mcmaster.nut_subtype import infer_nut_category_id, is_nut_line


def test_ambiguous_nut_defaults_hex():
    assert infer_nut_category_id("M4 nut") == "hex_nut"


def test_lock_nut_family():
    assert infer_nut_category_id("M5 lock nut") == "lock_nut"
    assert infer_nut_category_id("M3 nylock") == "lock_nut"
    assert infer_nut_category_id("nylock M3") == "lock_nut"


def test_flange_jam_coupling_families():
    assert infer_nut_category_id("M6 flange nut") == "flange_nut"
    assert infer_nut_category_id("M8 jam nut") == "jam_nut"
    assert infer_nut_category_id("M10 coupling nut") == "coupling_nut"


def test_is_nut_line_includes_nylock_without_nut_word():
    assert is_nut_line("nylock M3")
