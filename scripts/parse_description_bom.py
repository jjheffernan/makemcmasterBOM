#!/usr/bin/env python3
"""CLI: extract BOM parts from a project description (rule-based, no AI)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from backend.services.description_bom import (
    extract_candidate_lines,
    html_to_text,
    parts_from_description,
    resolve_description_text,
)


def _load_text(path: Path | None) -> str:
    if path is None:
        return sys.stdin.read()
    return path.read_text(encoding="utf-8")


async def _fetch_url(url: str) -> str:
    from backend.services.makerworld_bom import extract_design, extract_next_data
    from backend.services.page_fetch import fetch_makerworld_html
    from backend.services.scraper import _extract_description
    from bs4 import BeautifulSoup

    html, _ = await fetch_makerworld_html(url)
    soup = BeautifulSoup(html, "lxml")
    design = extract_design(extract_next_data(html) or {})
    og = _extract_description(soup)
    return resolve_description_text(og, design)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Parse hardware BOM lines from MakerWorld-style descriptions (no AI).",
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="Text or HTML file (default: stdin)",
    )
    parser.add_argument(
        "--url",
        metavar="MAKERWORLD_URL",
        help="Fetch description from a MakerWorld project URL",
    )
    parser.add_argument(
        "--lines",
        action="store_true",
        help="Print matched candidate lines before parsing",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Print normalized plain text only",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON array of Part objects (default)",
    )
    args = parser.parse_args(argv)

    if args.url:
        raw = asyncio.run(_fetch_url(args.url))
    else:
        raw = _load_text(args.file)

    if args.text:
        print(html_to_text(raw))
        return 0

    if args.lines:
        lines, from_section = extract_candidate_lines(raw)
        for line in lines:
            print(line)
        if from_section:
            print("# (from BOM section header)", file=sys.stderr)
        return 0

    parts = parts_from_description(raw)
    if args.json or not args.lines:
        print(json.dumps([p.model_dump() for p in parts], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
