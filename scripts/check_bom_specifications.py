#!/usr/bin/env python3
"""Runtime check: validate BOM specification fields for metadata and drift."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from backend.models.part import Part
from backend.services.parsers.helpers.specification_checks import (
    check_parts_specifications,
    format_specification_issues,
)
from backend.services.parsers.upload import parse_upload_bytes


def _load_parts(path: Path | None) -> list[Part]:
    if path is None:
        raw = json.load(sys.stdin)
    else:
        if path.suffix.lower() == ".json" and path.read_text(encoding="utf-8").strip().startswith("["):
            raw = json.loads(path.read_text(encoding="utf-8"))
        else:
            return parse_upload_bytes(path.read_bytes(), path.name)

    if isinstance(raw, list):
        return [Part.model_validate(item) for item in raw]
    if isinstance(raw, dict) and "parts" in raw:
        return [Part.model_validate(item) for item in raw["parts"]]
    raise SystemExit("Expected parts JSON array, {\"parts\": [...]}, or a BOM file")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that specification fields hold metadata only (no qty/name drift).",
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="BOM file or JSON parts (default: stdin JSON)",
    )
    parser.add_argument(
        "--errors-only",
        action="store_true",
        help="Exit non-zero only on error-severity issues",
    )
    args = parser.parse_args(argv)

    parts = _load_parts(args.file)
    issues = check_parts_specifications(parts)
    if args.errors_only:
        issues = [i for i in issues if i.severity == "error"]

    print(format_specification_issues(issues))
    if issues:
        return 1
    print(f"OK — {len(parts)} part(s) passed specification checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
