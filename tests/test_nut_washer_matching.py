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
    assert "metric-hex-nuts" in matched.mcmaster_url
    assert matched.mcmaster_part_number == ""
    assert matched.mcmaster_category == "hex_nut"
    assert len(matched.browse_finish_options) == 1
    assert matched.browse_finish_options[0].finish_id == "metric"
    assert matched.selected_finish_id == "metric"
    assert matched.browse_finish_options[0].mcmaster_url == matched.mcmaster_url

    tiers = {candidate.link.tier for candidate in collect_scored_candidates("M3 nut", part)}
    assert "filtered_browse" in tiers


def test_m3_nut_category_alternative_uses_metric_table_not_search_query():
    part = Part(original_name="M3 Nut", specification="")
    matched = match_part(part)
    assert "metric-hex-nuts" in matched.mcmaster_url
    assert "thread-size~m3" in matched.mcmaster_url
    candidates = collect_scored_candidates("M3 nut", part)
    assert any("metric-hex-nuts" in candidate.link.url for candidate in candidates)


def test_m3_hex_nut_stainless_prefers_stainless_filtered_browse():
    part = Part(original_name="M3 Hex Nut", specification="18-8 stainless", quantity=4)
    matched = match_part(part)
    assert matched.match_tier == "filtered_browse"
    assert "stainless" in matched.mcmaster_url.lower()
    catalog_alt = next(
        (
            alt
            for alt in matched.match_alternatives
            if alt.mcmaster_part_number == "91828A113"
        ),
        None,
    )
    assert catalog_alt is not None
    assert catalog_alt.guess_scope == "same_size"


def test_m4_washer_filtered_browse():
    part = Part(original_name="M4 washer", specification="")
    matched = match_part(part)
    assert matched.match_tier == "filtered_browse"
    assert "flat-washers" in matched.mcmaster_url
    assert "metric-flat-washers" in matched.mcmaster_url
    assert "screw-size~m4" in matched.mcmaster_url
    assert matched.mcmaster_category == "flat_washer"


def test_m5_lock_washer_uses_general_lock_table():
    part = Part(original_name="M5 lock washer", specification="")
    matched = match_part(part)
    assert matched.match_tier == "filtered_browse"
    assert "lock-washers" in matched.mcmaster_url
    assert "screw-size~m5" in matched.mcmaster_url
    assert matched.mcmaster_category == "lock_washer"
    assert matched.selected_finish_id == "general"


def test_m5_spring_washer_uses_split_lock_table():
    part = Part(original_name="M5 spring washer", specification="")
    matched = match_part(part)
    assert matched.match_tier == "filtered_browse"
    assert "metric-split-lock-washers-for-socket-head-screws" in matched.mcmaster_url
    assert "screw-size~m5" in matched.mcmaster_url
    assert matched.mcmaster_category == "lock_washer"
    assert matched.selected_finish_id == "split_socket"


def test_m6_fender_washer_filtered_browse():
    part = Part(original_name="M6 fender washer", specification="")
    matched = match_part(part)
    assert matched.match_tier == "filtered_browse"
    assert "fender-washers" in matched.mcmaster_url
    assert "screw-size~m6" in matched.mcmaster_url
    assert matched.mcmaster_category == "fender_washer"


def test_nylock_m3_extracts_thread_spec():
    part = Part(original_name="nylock M3", specification="")
    spec = primary_fastener_spec(part)
    assert spec is not None
    assert spec.diameter_mm == 3.0
    assert spec.kind == "nut"


def test_m3_nylock_uses_nylon_insert_table():
    part = Part(original_name="M3 nylock", specification="")
    matched = match_part(part)
    assert matched.match_tier == "filtered_browse"
    assert "nylon-insert-hex-nuts" in matched.mcmaster_url
    assert "thread-size~m3" in matched.mcmaster_url
    assert matched.mcmaster_category == "lock_nut"
    assert matched.selected_finish_id == "metric"


def test_m4_lock_nut_filtered_browse():
    part = Part(original_name="M4 lock nut", specification="")
    matched = match_part(part)
    assert matched.match_tier == "filtered_browse"
    assert "nylon-insert-hex-nuts" in matched.mcmaster_url
    assert "thread-size~m4" in matched.mcmaster_url
    assert matched.mcmaster_category == "lock_nut"


def test_m5_flange_nut_filtered_browse():
    part = Part(original_name="M5 flange nut", specification="")
    matched = match_part(part)
    assert matched.match_tier == "filtered_browse"
    assert "flange-nuts" in matched.mcmaster_url
    assert "metric-flange-nuts" in matched.mcmaster_url
    assert "thread-size~m5" in matched.mcmaster_url
    assert matched.mcmaster_category == "flange_nut"
