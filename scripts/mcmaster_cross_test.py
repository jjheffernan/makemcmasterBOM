#!/usr/bin/env python3
"""
Cross-test McMaster matching across app matcher and notebook pipeline.

Curated cases: data/mcmaster_regression_urls.json

Usage:
  python scripts/mcmaster_cross_test.py              # offline (default, no network)
  python scripts/mcmaster_cross_test.py --live       # Playwright live browse fetch
  python scripts/mcmaster_cross_test.py --live --refresh
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("XDG_CACHE_HOME", str(REPO_ROOT / ".cache"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Fetch McMaster browse tables (requires Playwright + MCMASTER_BROWSE_RESOLVE_ENABLED=1)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Reserved for future browse response cache bypass",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=REPO_ROOT / "data" / "mcmaster_regression_urls.json",
        help="Path to regression catalog JSON",
    )
    args = parser.parse_args()

    from backend.services.vendors.mcmaster.cross_test import (
        format_cross_test_report,
        run_live_cross_test,
        run_offline_cross_test,
    )

    try:
        if args.live:
            os.environ["MCMASTER_BROWSE_RESOLVE_ENABLED"] = "1"
            results = asyncio.run(
                run_live_cross_test(args.catalog, refresh=args.refresh)
            )
        else:
            results = run_offline_cross_test(args.catalog)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        if args.live:
            print(
                "\nTip: pip install -e '.[playwright]' && playwright install chromium",
                file=sys.stderr,
            )
        return 1

    print(format_cross_test_report(results))
    failed = [r for r in results if not r.ok]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
