#!/usr/bin/env python3
"""Crawl McMaster /products/ taxonomy via ProdPageWebPart (Playwright).

Writes data/mcmaster_site_taxonomy.json with top-level nav validation and
child-page product-family tiles grouped by McMaster department header.

Usage:
    python scripts/crawl_mcmaster_taxonomy.py
    python scripts/crawl_mcmaster_taxonomy.py --fastening-only
    python scripts/crawl_mcmaster_taxonomy.py --batch
    python scripts/crawl_mcmaster_taxonomy.py --batch --sync-metacategories

Batch mode (--batch) is intended for the monthly scheduled job:
  - fastening child pages only (reliable ProdPageWebPart responses)
  - polite delay between page fetches (default 5s, override with --delay)
  - crawled_at metadata and non-zero exit when too many pages fail
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.services.vendors.mcmaster.browse_scrape import fetch_product_presentations

DEFAULT_BATCH_DELAY_SECONDS = float(os.getenv("MCMASTER_CRAWL_DELAY_SECONDS", "5"))
DEFAULT_MAX_ERRORS = int(os.getenv("MCMASTER_CRAWL_MAX_ERRORS", "3"))

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

TAXONOMY_PATH = REPO_ROOT / "data" / "mcmaster_site_taxonomy.json"
METACATEGORIES_PATH = REPO_ROOT / "data" / "mcmaster_metacategories.json"


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


def fastening_families_from_taxonomy(taxonomy: dict) -> dict[str, str]:
    families: dict[str, str] = {}
    for page in taxonomy.get("fastening_children", {}).values():
        for group in page.get("groups", []):
            if group.get("department") != "Fastening and Joining":
                continue
            for tile in group.get("tiles", []):
                base = normalize_slug(tile["slug"])
                families[base] = tile["title"]
    return families


def summarize(taxonomy: dict) -> dict:
    families = fastening_families_from_taxonomy(taxonomy)
    return {
        "top_level_pages": len(taxonomy.get("top_level", {})),
        "fastening_child_pages": len(taxonomy.get("fastening_children", {})),
        "fastening_product_families": len(families),
        "errors": len(taxonomy.get("errors", [])),
    }


async def crawl_page(slug: str) -> dict:
    url = f"https://www.mcmaster.com/products/{slug}/"
    data = await fetch_product_presentations(url)
    return {"slug": slug, "url": url, "groups": extract_groups(data)}


async def run_crawl(
    *,
    fastening_only: bool,
    delay_seconds: float,
) -> dict:
    crawled_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    mode = "fastening_children" if fastening_only else "full"
    out: dict = {
        "version": 1,
        "crawled_at": crawled_at,
        "crawl_mode": mode,
        "delay_seconds": delay_seconds,
        "top_level": {},
        "fastening_children": {},
        "errors": [],
    }

    async def _crawl_with_delay(slug: str, bucket: dict) -> None:
        try:
            bucket[slug] = await crawl_page(slug)
            print(f"crawled {slug}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001
            out["errors"].append({"slug": slug, "error": str(exc)})
            print(f"error {slug}: {exc}", file=sys.stderr)
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)

    if not fastening_only:
        for slug, _label in TOP_SLUGS:
            await _crawl_with_delay(slug, out["top_level"])

    for slug in FASTENING_CHILD_PAGES:
        await _crawl_with_delay(slug, out["fastening_children"])

    out["summary"] = summarize(out)
    return out


def sync_metacategory_slugs(taxonomy: dict) -> dict[str, int]:
    """Merge crawled fastening families into mcmaster_metacategories product_slugs."""
    if not METACATEGORIES_PATH.is_file():
        raise FileNotFoundError(METACATEGORIES_PATH)

    meta = json.loads(METACATEGORIES_PATH.read_text(encoding="utf-8"))
    product_slugs: dict[str, str] = dict(meta.get("product_slugs", {}))
    families = fastening_families_from_taxonomy(taxonomy)

    added = 0
    for slug in families:
        if product_slugs.get(slug) != "fastening_and_joining":
            product_slugs[slug] = "fastening_and_joining"
            added += 1

    audit = dict(meta.get("coverage_audit", {}))
    audit.update(
        {
            "last_taxonomy_crawl": taxonomy.get("crawled_at"),
            "fastening_product_families_crawled": len(families),
            "product_slug_mappings": len(product_slugs),
        }
    )
    meta["product_slugs"] = dict(sorted(product_slugs.items()))
    meta["coverage_audit"] = audit
    METACATEGORIES_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return {"families": len(families), "slugs_added_or_updated": added}


def write_taxonomy(taxonomy: dict, path: Path = TAXONOMY_PATH) -> None:
    path.write_text(json.dumps(taxonomy, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fastening-only",
        action="store_true",
        help="Skip top-level department pages (often slower / flaky).",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help=(
            "Monthly batch defaults: fastening-only, polite delay, exit non-zero "
            "when too many pages fail."
        ),
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help=f"Seconds to wait between page fetches (batch default: {DEFAULT_BATCH_DELAY_SECONDS}).",
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        default=DEFAULT_MAX_ERRORS,
        help="Exit 1 when error count exceeds this threshold (batch mode).",
    )
    parser.add_argument(
        "--sync-metacategories",
        action="store_true",
        help="Merge crawled fastening slugs into data/mcmaster_metacategories.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=TAXONOMY_PATH,
        help="Output path for taxonomy JSON.",
    )
    args = parser.parse_args()

    fastening_only = args.fastening_only or args.batch
    delay_seconds = args.delay
    if delay_seconds is None:
        delay_seconds = DEFAULT_BATCH_DELAY_SECONDS if args.batch else 0.0

    taxonomy = asyncio.run(
        run_crawl(fastening_only=fastening_only, delay_seconds=delay_seconds)
    )
    write_taxonomy(taxonomy, args.output)
    print(json.dumps(taxonomy["summary"], indent=2))
    print(f"Wrote {args.output}")

    if args.sync_metacategories:
        stats = sync_metacategory_slugs(taxonomy)
        print(f"Synced metacategories: {stats}")

    if args.batch and taxonomy["summary"]["errors"] > args.max_errors:
        print(
            f"Too many crawl errors ({taxonomy['summary']['errors']} > {args.max_errors})",
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
