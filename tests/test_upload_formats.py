"""Tests for multi-format BOM upload parsing."""

import asyncio
import json
from pathlib import Path

import pytest

from backend.services.parsers.upload import parse_upload_bytes
from backend.services.pipeline import import_from_file

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_json_parts_array():
    payload = json.dumps(
        [{"quantity": 2, "original_name": "M3 bolt", "specification": "16 mm"}]
    ).encode()
    parts = parse_upload_bytes(payload, "bom.json")
    assert len(parts) == 1
    assert parts[0].quantity == 2
    assert "m3" in parts[0].original_name.lower()


def test_parse_json_parts_wrapper():
    payload = json.dumps({"parts": [{"quantity": 1, "original_name": "M4 washer"}]}).encode()
    parts = parse_upload_bytes(payload, "parts.json")
    assert len(parts) == 1
    assert "washer" in parts[0].original_name.lower()


def test_parse_markdown_description_fixture():
    text = (FIXTURES / "description_mega_python.txt").read_text(encoding="utf-8")
    parts = parse_upload_bytes(text.encode(), "bom.md")
    assert len(parts) >= 10


def test_parse_html_description_fixture():
    html = (FIXTURES / "description_material_required.html").read_text(encoding="utf-8")
    parts = parse_upload_bytes(html.encode(), "bom.html")
    assert any("magnet" in p.original_name.lower() for p in parts)


def test_parse_makerworld_design_json_fixture():
    design = json.loads((FIXTURES / "makerworld_magnet_design.json").read_text())
    parts = parse_upload_bytes(json.dumps(design).encode(), "design.json")
    assert len(parts) == 1
    assert "magnet" in parts[0].original_name.lower()


def test_import_from_file_rejects_unknown_extension():
    with pytest.raises(ValueError, match="Unsupported"):
        asyncio.run(import_from_file(b"data", "bom.pdf"))


def test_import_from_file_json():
    content = json.dumps([{"quantity": 1, "original_name": "M3 screw"}]).encode()
    project = asyncio.run(import_from_file(content, "bom.json"))
    assert len(project.parts) == 1
