"""Tests for head-type category routing and simplest default row selection."""

from backend.models.part import Part
from backend.services.matcher import match_part
from backend.services.mcmaster_catalog import catalog_lookup
from backend.services.mcmaster_handler import classify_category, infer_screw_head_type
from backend.services.vendors.mcmaster.browse_parse import BrowseRow
from backend.services.vendors.mcmaster.browse_row_select import (
    pick_simplest_browse_row,
)


def test_infer_screw_head_type_flat_vs_socket():
    assert infer_screw_head_type("M3x8 flat head cap screw") == "flat_head"
    assert infer_screw_head_type("M3x8 countersunk screw") == "flat_head"
    assert infer_screw_head_type("M3x8 countersink screw") == "flat_head"
    assert infer_screw_head_type("M3x8 socket head cap screw") == "socket_head"
    assert infer_screw_head_type("M3x8 screw") is None


def test_countersink_screw_routes_flat_head_category():
    part = Part(original_name="M3x8 countersink screw", specification="")
    matched = match_part(part)
    assert matched.mcmaster_category == "flat_head_screw"
    assert "socket-flat-head-screws" in matched.mcmaster_url
    assert "socket-head-screws" not in matched.mcmaster_url


def test_countersink_screw_not_socket_catalog_rule():
    hit = catalog_lookup("M3x8 countersink screw")
    assert hit is None


def test_classify_flat_head_escapes_socket_default():
    match = classify_category("M3x8 flat head cap screw")
    assert match.category.id == "flat_head_screw"
    assert match.method in {"signal", "head_type"}


def test_classify_bare_metric_screw_defaults_socket_head():
    match = classify_category("M3x8 screw")
    assert match.category.id == "socket_head_screw"
    assert match.method in {"metric", "metric_default"}


def test_pick_simplest_browse_row_prefers_standard_hex_nut():
    part = Part(original_name="M3 Nut")
    rows = [
        BrowseRow(
            part_number="90591A121",
            fields={"Thread Size": "M3", "Type": "Jam Nut"},
            product_subtype="Jam Nuts",
        ),
        BrowseRow(
            part_number="90591A110",
            fields={"Thread Size": "M3", "Type": "Hex Nut"},
            product_subtype="Hex Nuts",
        ),
    ]
    picked = pick_simplest_browse_row(part, rows)
    assert picked is not None
    assert picked.part_number == "90591A110"
