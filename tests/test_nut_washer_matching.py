"""Tests for M3 nut / washer filtered browse matching."""

from backend.models.part import Part
from backend.services.hardware_spec import primary_fastener_spec
from backend.services.matcher import match_part
from backend.services.vendors.mcmaster.candidates import collect_scored_candidates


def test_m3_nut_extracts_thread_spec():
    part = Part(original_name="M3 Nut", specification="")
    spec = primary_fastener_spec(part)
    assert spec is not None
    assert spec.diameter_mm == 3.0
    assert spec.kind == "nut"
    assert spec.length_mm is None


def test_m3_nut_prefers_filtered_browse_over_stainless_catalog():
    part = Part(original_name="M3 Nut", specification="", quantity=4)
    matched = match_part(part)
    assert matched.match_tier == "filtered_browse"
    assert "thread-size~m3" in matched.mcmaster_url
    assert "hex-nuts" in matched.mcmaster_url
    assert "metric-hex-nuts" in matched.mcmaster_url
    assert matched.mcmaster_part_number == ""

    tiers = {candidate.link.tier for candidate in collect_scored_candidates("M3 nut", part)}
    assert "filtered_browse" in tiers


def test_m3_nut_category_alternative_uses_metric_table_not_search_query():
    part = Part(original_name="M3 Nut", specification="")
    matched = match_part(part)
    assert "metric-hex-nuts" in matched.mcmaster_url
    assert "thread-size~m3" in matched.mcmaster_url
    candidates = collect_scored_candidates("M3 nut", part)
    assert any("metric-hex-nuts" in candidate.link.url for candidate in candidates)


def test_m3_hex_nut_stainless_keeps_catalog_when_material_specified():
    part = Part(original_name="M3 Hex Nut", specification="18-8 stainless", quantity=4)
    matched = match_part(part)
    assert matched.match_tier == "catalog"
    assert matched.mcmaster_part_number == "91828A113"


def test_m4_washer_filtered_browse():
    part = Part(original_name="M4 washer", specification="")
    matched = match_part(part)
    assert matched.match_tier == "filtered_browse"
    assert "flat-washers" in matched.mcmaster_url
    assert "thread-size~m4" in matched.mcmaster_url
