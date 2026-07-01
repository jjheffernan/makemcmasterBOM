#!/usr/bin/env python3
"""
McMaster browse table demo — offline fixture parse or live Playwright fetch.

Usage:
  python scripts/mcmaster_browse_example.py           # live (needs MCMASTER_BROWSE_RESOLVE_ENABLED=1)
  python scripts/mcmaster_browse_example.py --offline # fixture-only parse demo
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _offline_demo() -> None:
    from backend.notebook_frames import browse_rows_to_dataframe
    from backend.services.vendors.mcmaster.browse_parse import parse_product_presentations

    fixture = REPO_ROOT / "tests" / "fixtures" / "mcmaster_product_presentations_min.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    rows = parse_product_presentations(payload)
    df = browse_rows_to_dataframe(rows)
    print("Offline fixture parse (ProductPresentations → BrowseRow → DataFrame):")
    print(df.to_string(index=False))


async def _live_demo() -> None:
    from backend.notebook_frames import browse_rows_to_dataframe
    from backend.services.vendors.mcmaster.browse_fetch import fetch_browse_rows

    os.environ.setdefault("MCMASTER_BROWSE_RESOLVE_ENABLED", "1")
    url = (
        "https://www.mcmaster.com/products/screws/socket-head-screws-2~/"
        "black-oxide-alloy-steel-socket-head-screws~~/"
        "system-of-measurement~metric/thread-size~m3/length~16-mm/"
    )
    rows = await fetch_browse_rows(url)
    df = browse_rows_to_dataframe(rows)
    print(f"Live browse fetch ({len(rows)} rows):")
    print(df.head(10).to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Parse local ProductPresentations fixture (no network)",
    )
    args = parser.parse_args()

    try:
        if args.offline:
            _offline_demo()
        else:
            import asyncio

            asyncio.run(_live_demo())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        if not args.offline:
            print(
                "\nTip: pip install -e '.[playwright]' && playwright install chromium",
                file=sys.stderr,
            )
            print(
                "Set MCMASTER_BROWSE_RESOLVE_ENABLED=1 for live fetch, "
                "or run: python scripts/mcmaster_browse_example.py --offline",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
