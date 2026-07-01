#!/usr/bin/env python3
"""Runtime check: verify BOM hardware size and length match McMaster catalog hits."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from backend.models.part import Part
from backend.services.hardware_match_verify import verify_hardware_match
from backend.services.hardware_spec import primary_fastener_spec
from backend.services.matcher import match_part
from backend.services.mcmaster_catalog import catalog_lookup


def _load_parts(path: Path | None) -> list[Part]:
    if path is None:
        raw = json.load(sys.stdin)
    else:
        raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [Part.model_validate(item) for item in raw]
    if isinstance(raw, dict) and "parts" in raw:
        return [Part.model_validate(item) for item in raw["parts"]]
    raise SystemExit("Expected JSON array of parts or {\"parts\": [...]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check hardware size/length against McMaster catalog matches.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="JSON parts file (default: stdin)",
    )
    parser.add_argument(
        "--match",
        action="store_true",
        help="Run matcher before checking (default: check existing match fields)",
    )
    args = parser.parse_args(argv)

    parts = _load_parts(args.file)
    issues: list[str] = []

    for i, part in enumerate(parts):
        checked = match_part(part) if args.match else part
        hit = (
            catalog_lookup(checked.normalized_name or checked.original_name)
            if checked.mcmaster_part_number
            else None
        )
        if args.match:
            result = verify_hardware_match(checked, hit=hit)
            status = checked.hardware_match_status
        else:
            result = verify_hardware_match(checked, hit=hit)
            status = result.status

        if status in {"verified", "corrected", "unchecked", "not_applicable"}:
            continue

        primary = primary_fastener_spec(part)
        label = primary.label() if primary else part.original_name
        issues.append(
            f"[{status}] part {i + 1} {label!r}: {result.message or checked.mcmaster_reason}"
        )

    if issues:
        print(f"Found {len(issues)} hardware match issue(s):\n")
        print("\n".join(issues))
        return 1

    print(f"OK — {len(parts)} part(s) passed size/length checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
