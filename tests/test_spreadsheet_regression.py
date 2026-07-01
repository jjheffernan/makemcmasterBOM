"""Regression tests for captured MakerWorld-style spreadsheet exports."""

from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook

from backend.services.matcher import match_parts
from backend.services.parsers.upload import parse_upload_bytes
from backend.services.pipeline import import_from_file

FIXTURES = Path(__file__).parent / "fixtures"
MAKERWORLD_CSV = FIXTURES / "makerworld_export_bom.csv"


def _makerworld_xlsx_bytes() -> bytes:
  wb = Workbook()
  ws = wb.active
  ws.title = "BOM"
  ws.append(["Qty", "Product", "Spec"])
  ws.append([3, "M3x20 Socket Head Cap Screw", "Alloy steel"])
  ws.append([1, "M3 Washer", "Flat"])
  buffer = BytesIO()
  wb.save(buffer)
  return buffer.getvalue()


def test_parse_makerworld_csv_export_fixture():
    content = MAKERWORLD_CSV.read_bytes()
    parts = parse_upload_bytes(content, "makerworld_bom.csv")
    assert len(parts) == 4
    assert parts[0].quantity == 6
    assert "socket head" in parts[0].original_name.lower()
    assert parts[0].specification


def test_parse_makerworld_xlsx_export_variant():
    parts = parse_upload_bytes(_makerworld_xlsx_bytes(), "makerworld_bom.xlsx")
    assert len(parts) == 2
    assert parts[0].quantity == 3
    assert "m3" in parts[0].original_name.lower()


def test_match_makerworld_csv_export_fixture():
    parts = parse_upload_bytes(MAKERWORLD_CSV.read_bytes(), "makerworld_bom.csv")
    matched = match_parts(parts)
    by_name = {p.original_name: p for p in matched}

    screw = by_name["M3x16 Socket Head Cap Screw"]
    assert screw.match_tier == "filtered_browse"
    assert screw.confidence >= 0.86
    catalog_alt = next(
        (a for a in screw.match_alternatives if a.mcmaster_part_number == "91290A120"),
        None,
    )
    assert catalog_alt is not None

    bearing = by_name["608-ZZ Ball Bearing"]
    assert bearing.mcmaster_part_number
    assert bearing.mcmaster_url.startswith("https://www.mcmaster.com/")

    spacer = by_name["Custom printed spacer"]
    assert spacer.mcmaster_status == "not_applicable"


def test_import_from_file_makerworld_xlsx_pipeline():
    project = asyncio.run(import_from_file(_makerworld_xlsx_bytes(), "export.xlsx"))
    assert len(project.parts) == 2
    assert project.bom_status == "upload"
    assert all(p.mcmaster_url or p.mcmaster_status == "not_applicable" for p in project.parts)
