"""Tests for McMaster site category routing."""

import pytest

from backend.models.part import Part
from backend.services.matcher import match_part
from backend.services.mcmaster_handler import (
    McMasterCategory,
    STANDARD_COMPONENTS_ROUTE,
    build_mcmaster_link,
    category_search_url,
    classify_category,
    list_categories,
    site_search_url,
)


@pytest.mark.parametrize(
    ("query", "category_id"),
    [
        ("M3x8 socket head cap screw", "socket_head_screw"),
        ("608-ZZ bearing", "bearing"),
        ("M3 hex nut", "nut"),
        ("M3 flat washer", "washer"),
        ("PTFE tubing 2.5mm", "tubing"),
        ("neodymium magnet 10x3", "magnet"),
    ],
)
def test_classify_category_common_hardware(query, category_id):
    match = classify_category(query)
    assert match.category.id == category_id


def test_build_mcmaster_link_unclassified_without_site_search():
    link = build_mcmaster_link(
        "random widget bracket",
        part=Part(original_name="random widget bracket"),
    )
    assert link.link_type == "site_search"
    assert link.url == ""
    assert link.method == "unclassified"
    assert link.category_id == "unclassified"


def test_classify_unclassified_not_standard_components():
    match = classify_category("random widget bracket")
    assert match.category.id == "unclassified"
    assert match.method == "unclassified"
    assert "standard-components" not in match.category.route


def test_category_search_url_blocks_standard_components():
    blocked = McMasterCategory(
        id="standard_components",
        label="Standard Components",
        route=STANDARD_COMPONENTS_ROUTE,
        catalog_categories=(),
        priority=0,
        signals=(),
    )
    assert category_search_url(blocked, "widget bracket") == ""


def test_site_search_url_returns_empty():
    assert site_search_url("anything") == ""


def test_build_mcmaster_link_catalog_product():
    from backend.services.mcmaster_catalog import catalog_lookup

    hit = catalog_lookup("M3x8 socket head cap screw")
    assert hit is not None
    link = build_mcmaster_link("M3x8 socket head cap screw", catalog_hit=hit)
    assert link.link_type == "product"
    assert link.url.startswith(f"https://www.mcmaster.com/{hit.part_number}/")
    assert "searchQuery=" in link.url
    assert link.category_id == "socket_head_screw"


def test_match_part_search_uses_category_route():
    matched = match_part(Part(original_name="M5x12 hex bolt", specification=""))
    assert "searchQuery=" in matched.mcmaster_url
    assert matched.match_tier in {"filtered_browse", "category_search"}
    assert matched.mcmaster_category == "screw"


def test_list_categories_not_empty():
    assert len(list_categories()) >= 10
