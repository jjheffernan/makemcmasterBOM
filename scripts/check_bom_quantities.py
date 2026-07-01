#!/usr/bin/env python3
"""Runtime check: flag BOM rows where quantity landed in the wrong field."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from backend.services.description_bom import (
    extract_candidate_lines,
    parts_from_description,
    resolve_description_text,
)
from backend.services.parsers.helpers.quantity_checks import (
    check_part,
    check_parsed_line,
    format_issues,
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
        description="Check that BOM quantities are in QTY, not embedded in specification.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="Description text/HTML file (default: stdin)",
    )
    parser.add_argument(
        "--url",
        metavar="MAKERWORLD_URL",
        help="Fetch description from a MakerWorld project URL",
    )
    parser.add_argument(
        "--lines-only",
        action="store_true",
        help="Validate raw candidate lines only (skip Part assembly)",
    )
    args = parser.parse_args(argv)

    if args.url:
        raw = asyncio.run(_fetch_url(args.url))
    else:
        raw = _load_text(args.file)

    if args.lines_only:
        lines, _ = extract_candidate_lines(raw)
        line_issues: list[str] = []
        for i, line in enumerate(lines):
            for msg in check_parsed_line(line):
                line_issues.append(f"line {i + 1}: {msg}\n  {line!r}")
        if line_issues:
            print("Quantity issues in candidate lines:\n")
            print("\n".join(line_issues))
            return 1
        print(f"OK — {len(lines)} candidate line(s) passed quantity checks.")
        return 0

    lines, _ = extract_candidate_lines(raw)
    parts = parts_from_description(raw)
    issues = []
    for i, part in enumerate(parts):
        source = lines[i] if i < len(lines) else None
        issues.extend(check_part(part, index=i, source_line=source))

    print(format_issues(issues))
    if issues:
        return 1
    print(f"OK — {len(parts)} part(s) passed quantity checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
