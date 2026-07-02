"""McMaster metacategory (product department) mapping tests."""

import json
from pathlib import Path

from backend.models.part import Part
from backend.services.matcher import match_part
from backend.services.vendors.mcmaster.metacategories import (
    infer_bom_metacategory,
    metacategory_for_category_id,
    metacategory_for_route,
    metacategory_for_slug,
    resolve_link_metacategory,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CATEGORIES_PATH = REPO_ROOT / "data" / "mcmaster_categories.json"
METACATEGORIES_PATH = REPO_ROOT / "data" / "mcmaster_metacategories.json"


def test_all_bom_categories_have_metacategory():
    categories = json.loads(CATEGORIES_PATH.read_text())["categories"]
    mapping = json.loads(METACATEGORIES_PATH.read_text())["category_metacategory"]
    missing = [item["id"] for item in categories if item["id"] not in mapping]
    assert not missing, f"Unmapped categories: {missing}"


def test_fastener_bom_intent():
    assert infer_bom_metacategory("M3x16 socket head cap screw") == "fastening_and_joining"
    assert infer_bom_metacategory("608-ZZ bearing") == "power_transmission"
    assert infer_bom_metacategory("M3 o-ring") == "sealing"


def test_tile_slug_normalization():
    assert metacategory_for_slug("socket-head-screws-2~") == "fastening_and_joining"


def test_category_and_slug_lookup():
    assert metacategory_for_category_id("hex_nut") == "fastening_and_joining"
    assert metacategory_for_slug("screws") == "fastening_and_joining"
    assert metacategory_for_route("/products/ball-bearings/") == "power_transmission"


def test_match_part_sets_metacategory():
    matched = match_part(Part(original_name="M3 Nut"))
    assert matched.mcmaster_metacategory == "fastening_and_joining"
    assert matched.mcmaster_metacategory_label == "Fastening & Joining"


def test_resolve_link_from_filtered_browse():
    meta = resolve_link_metacategory(
        category_id="hex_nut",
        url="https://www.mcmaster.com/products/metric-hex-nuts/system-of-measurement~metric/thread-size~m3/",
    )
    assert meta == "fastening_and_joining"
