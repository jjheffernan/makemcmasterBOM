"""Unit tests for taxonomy crawl helpers (no network)."""

import json
from pathlib import Path

from scripts.crawl_mcmaster_taxonomy import (
    fastening_families_from_taxonomy,
    normalize_slug,
    summarize,
    sync_metacategory_slugs,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = REPO_ROOT / "data" / "mcmaster_site_taxonomy.json"
METACATEGORIES_PATH = REPO_ROOT / "data" / "mcmaster_metacategories.json"


def test_normalize_slug_strips_mcmaster_tile_suffix():
    assert normalize_slug("socket-head-screws-2~") == "socket-head-screws"
    assert normalize_slug("metric-flat-washers~~") == "metric-flat-washers"


def test_summarize_taxonomy_fixture():
    if not TAXONOMY_PATH.is_file():
        return
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    summary = summarize(taxonomy)
    assert summary["fastening_child_pages"] >= 1
    assert summary["fastening_product_families"] >= 50


def test_sync_metacategory_slugs_idempotent(tmp_path, monkeypatch):
    meta_src = json.loads(METACATEGORIES_PATH.read_text(encoding="utf-8"))
    meta_copy = tmp_path / "meta.json"
    meta_copy.write_text(json.dumps(meta_src, indent=2), encoding="utf-8")

    taxonomy = {
        "fastening_children": {
            "screws": {
                "groups": [
                    {
                        "department": "Fastening and Joining",
                        "tiles": [{"slug": "brand-new-family-2~", "title": "Brand New Family"}],
                    }
                ]
            }
        }
    }

    import scripts.crawl_mcmaster_taxonomy as crawl_mod

    monkeypatch.setattr(crawl_mod, "METACATEGORIES_PATH", meta_copy)
    first = sync_metacategory_slugs(taxonomy)
    second = sync_metacategory_slugs(taxonomy)
    assert first["slugs_added_or_updated"] >= 1
    assert second["slugs_added_or_updated"] == 0
    updated = json.loads(meta_copy.read_text(encoding="utf-8"))
    assert updated["product_slugs"]["brand-new-family"] == "fastening_and_joining"


def test_fastening_families_from_taxonomy():
    taxonomy = {
        "fastening_children": {
            "nuts": {
                "groups": [
                    {
                        "department": "Fastening and Joining",
                        "tiles": [{"slug": "hex-nuts-5~", "title": "Hex Nuts"}],
                    },
                    {
                        "department": "Power Transmission",
                        "tiles": [{"slug": "bearing-nuts-2~", "title": "Bearing Nuts"}],
                    },
                ]
            }
        }
    }
    families = fastening_families_from_taxonomy(taxonomy)
    assert families == {"hex-nuts": "Hex Nuts"}
