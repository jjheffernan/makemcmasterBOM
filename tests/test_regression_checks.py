"""Regression checks — CLI validators must pass on golden fixtures."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from backend.services.description_bom import parts_from_description
from backend.services.matcher import match_parts

from tests.conftest import REPO_ROOT

FIXTURES = Path(__file__).parent / "fixtures"
MEGA_PYTHON = FIXTURES / "description_mega_python.txt"
SAMPLE_BOM = REPO_ROOT / "data" / "sample_bom.csv"


def test_check_bom_quantities_script_passes_mega_python_fixture() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "check_bom_quantities.py"),
            str(MEGA_PYTHON),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"check_bom_quantities failed (exit {result.returncode}):\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_check_hardware_specs_script_passes_matched_mega_python() -> None:
    parts = match_parts(parts_from_description(MEGA_PYTHON.read_text()))
    payload = json.dumps([p.model_dump() for p in parts])

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "check_hardware_specs.py"),
            "--match",
        ],
        cwd=REPO_ROOT,
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"check_hardware_specs failed (exit {result.returncode}):\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_check_bom_specifications_script_passes_sample_bom() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "check_bom_specifications.py"),
            str(SAMPLE_BOM),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"check_bom_specifications failed (exit {result.returncode}):\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_check_catalog_integrity_script_passes() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "check_catalog_integrity.py"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"check_catalog_integrity failed (exit {result.returncode}):\n"
        f"{result.stdout}\n{result.stderr}"
    )
