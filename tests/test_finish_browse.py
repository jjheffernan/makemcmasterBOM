"""Filtered-browse finish variant tests."""

from backend.models.part import Part
from backend.services.matcher import match_part
from backend.services.vendors.mcmaster.finish_browse import (
    applicable_finish_roots,
    build_browse_finish_options,
)
from backend.services.vendors.mcmaster.filters import infer_finish_from_bom


def test_infer_finish_from_bom_detects_named_finishes():
    assert infer_finish_from_bom("M3x8 screw", "Stainless") == "stainless"
    assert infer_finish_from_bom("M3x8 screw", "zinc plated") == "zinc_plated"
    assert infer_finish_from_bom("M3x8 screw", "black oxide") == "black_oxide"
    assert infer_finish_from_bom("M3x8 screw", "alloy steel") == "black_oxide"
    assert infer_finish_from_bom("M3x8 socket head cap screw", "") is None


def test_applicable_finish_roots_ambiguous_screw_defaults_black_oxide():
    roots = applicable_finish_roots("socket_head_screw", "M3x16 socket head cap screw", "")
    assert len(roots) == 1
    assert roots[0].finish_id == "black_oxide"


def test_applicable_finish_roots_ambiguous_nut_uses_metric_table():
    roots = applicable_finish_roots("hex_nut", "M3 nut", "")
    assert len(roots) == 1
    assert roots[0].finish_id == "metric"
    assert "metric-hex-nuts" in roots[0].route


def test_applicable_finish_roots_stainless_only():
    roots = applicable_finish_roots(
        "socket_head_screw",
        "M3x8 socket head cap screw",
        "18-8 stainless",
    )
    assert len(roots) == 1
    assert roots[0].finish_id == "stainless"


def test_build_browse_finish_options_share_thread_length_filters():
    part = Part(original_name="M3x16 socket head cap screw")
    options = build_browse_finish_options(
        "M3x16 socket head cap screw",
        part,
        category_id="socket_head_screw",
        filter_path="system-of-measurement~metric/thread-size~m3/length~16-mm/",
    )
    assert len(options) == 1
    assert options[0].finish_id == "black_oxide"
    assert "thread-size~m3" in options[0].mcmaster_url
    assert "length~16-mm" in options[0].mcmaster_url


def test_match_part_ambiguous_screw_single_default_finish():
    matched = match_part(Part(original_name="M3x16 socket head cap screw"))
    assert matched.match_tier == "filtered_browse"
    assert len(matched.browse_finish_options) == 1
    assert matched.selected_finish_id == "black_oxide"
    assert "black-oxide-alloy-steel" in matched.mcmaster_url


def test_match_part_stainless_screw_single_finish_no_multi_options():
    matched = match_part(
        Part(original_name="M3x8 socket head cap screw", specification="Stainless")
    )
    assert matched.match_tier == "filtered_browse"
    assert len(matched.browse_finish_options) == 1
    assert matched.selected_finish_id == "stainless"
    assert "18-8-stainless-steel" in matched.mcmaster_url
