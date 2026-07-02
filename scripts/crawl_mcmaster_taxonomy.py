#!/usr/bin/env python3
"""Crawl McMaster /products/ taxonomy via ProdPageWebPart (Playwright).

Writes data/mcmaster_site_taxonomy.json with top-level nav validation and
child-page product-family tiles grouped by McMaster department header.

Usage:
    python scripts/crawl_mcmaster_taxonomy.py
    python scripts/crawl_mcmaster_taxonomy.py --fastening-only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.services.vendors.mcmaster.browse_scrape import fetch_product_presentations

TOP_SLUGS: list[tuple[str, str]] = [
    ("abrading-and-polishing", "Abrading & Polishing"),
    ("building-and-grounds", "Building & Grounds"),
    ("electrical-and-lighting", "Electrical & Lighting"),
    ("fabricating", "Fabricating"),
    ("fastening-and-joining", "Fastening & Joining"),
    ("filtering", "Filtering"),
    ("flow-and-level-control", "Flow & Level Control"),
    ("furniture-and-storage", "Furniture & Storage"),
    ("hand-tools", "Hand Tools"),
    ("hardware", "Hardware"),
    ("heating-and-cooling", "Heating & Cooling"),
    ("lubricating", "Lubricating"),
    ("material-handling", "Material Handling"),
    ("measuring-and-inspecting", "Measuring & Inspecting"),
    ("office-supplies-and-signs", "Office Supplies & Signs"),
    ("pipe-tubing-hose-and-fittings", "Pipe, Tubing, Hose & Fittings"),
    ("plumbing-and-janitorial", "Plumbing & Janitorial"),
    ("power-transmission", "Power Transmission"),
    ("pressure-and-temperature-control", "Pressure & Temperature Control"),
    ("pulling-and-lifting", "Pulling & Lifting"),
    ("raw-materials", "Raw Materials"),
    ("safety-supplies", "Safety Supplies"),
    ("sawing-and-cutting", "Sawing & Cutting"),
    ("sealing", "Sealing"),
    ("shipping", "Shipping"),
    ("suspending", "Suspending"),
]

FASTENING_CHILD_PAGES = [
    "screws",
    "nuts",
    "washers",
    "rivets",
    "pins",
    "standoffs",
    "threaded-rods",
    "anchors",
    "magnets",
    "shims",
    "retaining-rings",
    "cable-ties",
    "studs",
    "set-screws",
    "eyebolts",
    "u-bolts",
    "thread-adapters",
    "heat-set-inserts",
    "binding-barrels",
]


def _text_from_display(obj) -> str:
    if not obj:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        parts = obj.get("text") or obj.get("Text") or []
        return "".join(parts) if isinstance(parts, list) else str(parts)
    return str(obj)


def extract_groups(data: dict) -> list[dict]:
    groups: list[dict] = []

    def walk(obj) -> None:
        if isinstance(obj, dict):
            if "Groups" in obj and isinstance(obj["Groups"], list):
                for group in obj["Groups"]:
                    header = group.get("Header") or _text_from_display(group.get("HeaderDisplay"))
                    tiles: list[dict] = []
                    for tile in group.get("Tiles") or []:
                        href = tile.get("RelativeHref") or tile.get("relativeHref") or ""
                        if not href:
                            continue
                        slug = href.strip("/").split("/")[0]
                        title = _text_from_display(tile.get("Title")) or _text_from_display(
                            tile.get("DisplayName")
                        )
                        if not title:
                            for copy in tile.get("Copy") or []:
                                for cs in copy.get("CopyStructures") or []:
                                    for block in cs.get("Blocks") or []:
                                        for seg in block.get("Segments") or []:
                                            text = seg.get("Text")
                                            if text and tile.get("TileStyle") == "ProductOutline":
                                                title = text
                                                break
                        count = tile.get("ProductFamilyCount") or tile.get("ProductCount")
                        tiles.append(
                            {
                                "title": (title or slug).strip(),
                                "slug": slug,
                                "href": href,
                                "product_count": count,
                            }
                        )
                    if header or tiles:
                        groups.append({"department": header, "tiles": tiles})
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return groups


def normalize_slug(slug: str) -> str:
    normalized = slug.strip().lower()
    normalized = re.sub(r"-\d+~+$", "", normalized)
    return normalized.rstrip("~")


async def crawl_page(slug: str) -> dict:
    url = f"https://www.mcmaster.com/products/{slug}/"
    data = await fetch_product_presentations(url)
    return {"slug": slug, "url": url, "groups": extract_groups(data)}


async def run_crawl(*, fastening_only: bool) -> dict:
    out: dict = {"version": 1, "top_level": {}, "fastening_children": {}, "errors": []}
    if not fastening_only:
        for slug, _label in TOP_SLUGS:
            try:
                out["top_level"][slug] = await crawl_page(slug)
            except Exception as exc:  # noqa: BLE001
                out["errors"].append({"slug": slug, "error": str(exc)})
    for slug in FASTENING_CHILD_PAGES:
        try:
            out["fastening_children"][slug] = await crawl_page(slug)
        except Exception as exc:  # noqa: BLE001
            out["errors"].append({"slug": slug, "error": str(exc)})
    return out


def summarize(taxonomy: dict) -> dict:
    fastening_families: dict[str, str] = {}
    for page in taxonomy.get("fastening_children", {}).values():
        for group in page.get("groups", []):
            if group.get("department") != "Fastening and Joining":
                continue
            for tile in group.get("tiles", []):
                base = normalize_slug(tile["slug"])
                fastening_families[base] = tile["title"]
    return {
        "top_level_pages": len(taxonomy.get("top_level", {})),
        "fastening_child_pages": len(taxonomy.get("fastening_children", {})),
        "fastening_product_families": len(fastening_families),
        "errors": len(taxonomy.get("errors", [])),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fastening-only",
        action="store_true",
        help="Skip top-level department pages (often slower / flaky).",
    )
    args = parser.parse_args()

    taxonomy = asyncio.run(run_crawl(fastening_only=args.fastening_only))
    taxonomy["summary"] = summarize(taxonomy)

    out_path = REPO_ROOT / "data" / "mcmaster_site_taxonomy.json"
    out_path.write_text(json.dumps(taxonomy, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(taxonomy["summary"], indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
