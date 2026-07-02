"""Tests for McMaster part-number catalog lookup."""

import pytest

from backend.services.mcmaster_catalog import (
    catalog_lookup,
    catalog_stats,
    mcmaster_product_url,
    normalize_catalog_key,
)
from backend.services.matcher import match_part
from backend.models.part import Part


@pytest.mark.parametrize(
    ("query", "part_number"),
    [
        ("M3x8 socket head cap screw", "91290A110"),
        ("M3-16 mm socket head cap screw", "91290A120"),
        ("75 x M3-16 mm", "91290A120"),
        ("608-ZZ bearings", "5972K113"),
        ("693-ZZ bearing", "5972K42"),
        ("M3 hex nut stainless", "91828A113"),
    ],
)
def test_catalog_lookup_common_parts(query, part_number):
    hit = catalog_lookup(query)
    assert hit is not None
    assert hit.part_number == part_number
    assert mcmaster_product_url(hit.part_number).endswith(part_number)


def test_mcmaster_product_url_with_search_query():
    url = mcmaster_product_url("90273A010", "M3x25 screw")
    assert url == "https://www.mcmaster.com/90273A010/?searchQuery=M3x25+screw"


def test_normalize_catalog_key_metric_dash_form():
    assert normalize_catalog_key("M3-16 mm socket head") == "m3x16 socket head"


def test_catalog_stats_has_entries():
    stats = catalog_stats()
    assert stats["entries"] >= 10
    assert stats["keys"] >= 20


def test_match_part_uses_product_url_for_catalog_hit():
    matched = match_part(
        Part(original_name="M3-16 mm", specification="socket head cap screw")
    )
    assert matched.match_tier == "filtered_browse"
    assert "thread-size~m3" in matched.mcmaster_url
    assert matched.mcmaster_status == "likely"
    assert matched.confidence >= 0.86
    catalog_alt = next(
        (a for a in matched.match_alternatives if a.mcmaster_part_number == "91290A120"),
        None,
    )
    assert catalog_alt is not None
    assert catalog_alt.mcmaster_url.startswith("https://www.mcmaster.com/91290A120/")
    assert "searchQuery=" in catalog_alt.mcmaster_url


def test_match_part_without_catalog_hit_skips_site_search():
    matched = match_part(Part(original_name="custom widget bracket"))
    assert matched.mcmaster_part_number == ""
    assert matched.mcmaster_url == ""
    assert matched.mcmaster_status == "not_applicable"
    assert matched.match_tier == "not_applicable"
