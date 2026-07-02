"""Tier-aware McMaster match status and confidence."""

from backend.models.part import Part
from backend.services.matcher import match_part, resolve_match_status


def test_not_applicable_sets_match_tier():
    matched = match_part(Part(original_name="PLA printed spacer", specification="PETG"))
    assert matched.mcmaster_status == "not_applicable"
    assert matched.match_tier == "not_applicable"


def test_filtered_browse_tier_is_likely():
    matched = match_part(Part(original_name="M4x30 socket head cap screw"))
    assert matched.match_tier == "filtered_browse"
    assert matched.mcmaster_status == "likely"
    assert matched.confidence >= 0.65
    assert len(matched.match_alternatives) >= 1


def test_m3_screw_includes_catalog_sku_alternative():
    matched = match_part(Part(original_name="M3x16 socket head cap screw"))
    assert matched.match_tier == "filtered_browse"
    part_numbers = [matched.mcmaster_part_number] + [
        a.mcmaster_part_number for a in matched.match_alternatives
    ]
    assert "91290A120" in part_numbers


def test_stainless_spec_prefers_filtered_browse_over_black_oxide_catalog():
    matched = match_part(
        Part(original_name="M3x8 socket head cap screw", specification="Stainless")
    )
    assert matched.match_tier == "filtered_browse"
    assert "stainless" in matched.mcmaster_url.lower()
    catalog_alt = next(
        (a for a in matched.match_alternatives if a.match_tier in {"catalog", "rule"}),
        None,
    )
    assert catalog_alt is not None
    assert catalog_alt.confidence < matched.confidence


def test_category_search_tier_is_possible():
    matched = match_part(Part(original_name="#6-32 x 1/2\"", specification=""))
    assert matched.match_tier == "category_search"
    assert matched.mcmaster_status == "possible"


def test_unclassified_hardware_not_site_search():
    matched = match_part(Part(original_name="widget bracket", specification="aluminum"))
    assert matched.match_tier == "not_applicable"
    assert matched.mcmaster_status == "not_applicable"
    assert "standard-components" not in (matched.mcmaster_url or "")


def test_resolve_match_status_tier_table():
    assert resolve_match_status(0.75, "possible", tier="filtered_browse") == "likely"
    assert resolve_match_status(0.55, "possible", tier="category_search") == "possible"
    assert resolve_match_status(0.35, "possible", tier="site_search") == "possible"
    assert resolve_match_status(0.2, "possible", tier="site_search") == "unlikely"
    assert resolve_match_status(0.9, "unlikely", tier="catalog") == "unlikely"
