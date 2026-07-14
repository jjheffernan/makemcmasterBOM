"""Golden BOM corpus — parse score against locked expected.json fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.services.parsers.makerworld.description import parse_description_bom

GOLDEN_ROOT = Path(__file__).parent / "fixtures" / "golden_boms"


def _case_dirs() -> list[Path]:
    if not GOLDEN_ROOT.exists():
        return []
    return sorted(p for p in GOLDEN_ROOT.iterdir() if p.is_dir() and (p / "expected.json").exists())


def _normalize_name(name: str) -> str:
    return " ".join(name.lower().split())


def _score(actual_parts: list, expected_parts: list[dict]) -> tuple[float, list[str]]:
    """Return score in [0,1] and human-readable miss notes."""
    notes: list[str] = []
    if not expected_parts:
        return (1.0 if not actual_parts else 0.0, notes)

    expected_keys = [
        (_normalize_name(p["original_name"]), int(p.get("quantity") or 0))
        for p in expected_parts
    ]
    actual_keys = [
        (_normalize_name(p.original_name), int(p.quantity or 0)) for p in actual_parts
    ]

    matched = 0
    remaining = actual_keys.copy()
    for key in expected_keys:
        if key in remaining:
            remaining.remove(key)
            matched += 1
        else:
            notes.append(f"missing expected {key!r}")

    for extra in remaining:
        notes.append(f"unexpected actual {extra!r}")

    score = matched / len(expected_keys)
    return score, notes


@pytest.mark.parametrize("case_dir", _case_dirs(), ids=lambda p: p.name)
def test_golden_bom_parse_score(case_dir: Path):
    expected = json.loads((case_dir / "expected.json").read_text())
    text = (case_dir / "input.txt").read_text()
    assert expected.get("parser") == "description"

    result = parse_description_bom(text)
    score, notes = _score(result.parts, expected["parts"])
    assert score == 1.0, (
        f"{case_dir.name} score={score:.2%} ({len(result.parts)} actual / "
        f"{len(expected['parts'])} expected)\n" + "\n".join(notes)
    )
    assert bool(result.from_explicit_section) == bool(expected.get("from_explicit_section"))


def test_golden_corpus_has_at_least_eight_cases():
    assert len(_case_dirs()) >= 8
