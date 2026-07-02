"""McMaster category coverage and taxonomy validation."""

import json
import re
from pathlib import Path

import httpx
import pytest

from backend.services.vendors.mcmaster.metacategories import (
    list_metacategories,
    metacategory_for_category_id,
    metacategory_for_route,
    metacategory_for_slug,
    normalize_product_slug,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CATEGORIES_PATH = REPO_ROOT / "data" / "mcmaster_categories.json"
METACATEGORIES_PATH = REPO_ROOT / "data" / "mcmaster_metacategories.json"
TAXONOMY_PATH = REPO_ROOT / "data" / "mcmaster_site_taxonomy.json"

EXPECTED_TOP_LEVEL_LABELS = [
    "Abrading & Polishing",
    "Building & Grounds",
    "Electrical & Lighting",
    "Fabricating",
    "Fastening & Joining",
    "Filtering",
    "Flow & Level Control",
    "Furniture & Storage",
    "Hand Tools",
    "Hardware",
    "Heating & Cooling",
    "Lubricating",
    "Material Handling",
    "Measuring & Inspecting",
    "Office Supplies & Signs",
    "Pipe, Tubing, Hose & Fittings",
    "Plumbing & Janitorial",
    "Power Transmission",
    "Pressure & Temperature Control",
    "Pulling & Lifting",
    "Raw Materials",
    "Safety Supplies",
    "Sawing & Cutting",
    "Sealing",
    "Shipping",
    "Suspending",
]


def test_twenty_six_top_level_metacategories():
    metas = list_metacategories()
    assert len(metas) == 26
    labels = [item.label for item in metas]
    assert labels == EXPECTED_TOP_LEVEL_LABELS


def test_all_matcher_categories_have_metacategory():
    categories = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))["categories"]
    mapping = json.loads(METACATEGORIES_PATH.read_text(encoding="utf-8"))["category_metacategory"]
    missing = [item["id"] for item in categories if item["id"] not in mapping]
    assert not missing, f"Unmapped categories: {missing}"


def test_normalize_product_slug_strips_tile_suffix():
    assert normalize_product_slug("socket-head-screws-2~") == "socket-head-screws"
    assert normalize_product_slug("metric-flat-washers~~") == "metric-flat-washers"


def test_tile_slug_lookup_after_normalization():
    assert metacategory_for_slug("socket-head-screws-2~") == "fastening_and_joining"
    assert metacategory_for_slug("hex-nuts-5~") == "fastening_and_joining"


def test_reclassified_departments():
    assert metacategory_for_category_id("oring") == "sealing"
    assert metacategory_for_category_id("tubing") == "pipe_tubing_hose_and_fittings"
    assert metacategory_for_route("/products/o-rings/") == "sealing"


@pytest.mark.parametrize(
    "category_id,route",
    [
        ("set_screw", "/products/set-screws/"),
        ("threaded_rod", "/products/threaded-rods/"),
        ("anchor", "/products/anchors/"),
        ("retaining_ring", "/products/retaining-rings/"),
        ("cable_tie", "/products/cable-ties/"),
        ("threaded_insert", "/products/threaded-inserts/"),
    ],
)
def test_new_fastening_routes_map_to_department(category_id: str, route: str):
    assert metacategory_for_category_id(category_id) == "fastening_and_joining"
    assert metacategory_for_route(route) == "fastening_and_joining"


@pytest.mark.integration
def test_matcher_category_routes_resolve_http():
    categories = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))["categories"]
    failures: list[str] = []
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=30,
            headers={"User-Agent": "makemcmasterBOM-coverage-test/1"},
        ) as client:
            for item in categories:
                url = f"https://www.mcmaster.com{item['route']}"
                response = client.get(url)
                if response.status_code != 200:
                    failures.append(f"{item['id']}: {response.status_code} {item['route']}")
    except httpx.ConnectError:
        pytest.skip("McMaster unreachable (offline or sandbox)")
    assert not failures, "Broken routes:\n" + "\n".join(failures)


def test_crawled_fastening_families_map_to_fastening_department():
    if not TAXONOMY_PATH.is_file():
        pytest.skip("Run scripts/crawl_mcmaster_taxonomy.py to generate taxonomy fixture")

    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    unmapped: list[str] = []
    for page in taxonomy.get("fastening_children", {}).values():
        for group in page.get("groups", []):
            if group.get("department") != "Fastening and Joining":
                continue
            for tile in group.get("tiles", []):
                base = normalize_product_slug(tile["slug"])
                if metacategory_for_slug(base) != "fastening_and_joining":
                    unmapped.append(base)
    assert not unmapped, f"Unmapped fastening families: {sorted(set(unmapped))[:20]}"


def test_taxonomy_fixture_has_batch_metadata():
    if not TAXONOMY_PATH.is_file():
        pytest.skip("Run scripts/crawl_mcmaster_taxonomy.py to generate taxonomy fixture")

    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    assert taxonomy.get("summary")
    assert taxonomy["summary"]["fastening_child_pages"] >= 1
    # crawled_at added by batch crawl; optional for older fixtures
    if "crawled_at" in taxonomy:
        assert "T" in taxonomy["crawled_at"]
