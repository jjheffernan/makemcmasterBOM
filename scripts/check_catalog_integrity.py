#!/usr/bin/env python3
"""Runtime check: curated McMaster catalog keys, titles, and rule tables agree."""

from __future__ import annotations

import sys

from backend.services.catalog_integrity import check_catalog_integrity


def main() -> int:
    issues = check_catalog_integrity()
    if not issues:
        print("OK — catalog integrity checks passed.")
        return 0

    for issue in issues:
        print(f"{issue.code}: {issue.part_number} — {issue.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
