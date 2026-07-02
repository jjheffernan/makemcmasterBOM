"""Ensure Jupyter notebooks stay aligned with backend.services.pipeline (website flow)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from backend.models.part import Part
from backend.models.progress import PIPELINE_STAGES
from backend.notebook_pipeline import (
    FORBIDDEN_NOTEBOOK_PATTERNS,
    NOTEBOOKS_DIR,
    STAGE_ENTRY_POINTS,
    STAGE_NOTEBOOK,
    offline_file_import_parts,
    validate_pipeline_notebook_sync,
)
from backend.notebook_utils import load_local_bom_file
from backend.services.pipeline import import_from_file, match_parts_only, parse_bom_only

NUMBERED_NOTEBOOKS = (
    "01_scrape.ipynb",
    "02_extract_bom.ipynb",
    "03_parse_bom.ipynb",
    "04_match_mcmaster.ipynb",
    "05_api_payload.ipynb",
)


def _notebook_source(filename: str) -> str:
    path = NOTEBOOKS_DIR / filename
    raw = json.loads(path.read_text(encoding="utf-8"))
    chunks: list[str] = []
    for cell in raw.get("cells", []):
        if cell.get("cell_type") == "code":
            src = cell.get("source", "")
            chunks.append(src if isinstance(src, str) else "".join(src))
    return "\n".join(chunks)


def test_pipeline_notebook_files_exist():
    errors = validate_pipeline_notebook_sync()
    assert not errors, "\n".join(errors)


def test_pipeline_stages_reference_existing_notebooks():
    for stage in PIPELINE_STAGES:
        path = NOTEBOOKS_DIR / stage["notebook"]
        assert path.is_file(), f"Stage {stage['id']} → missing {path}"


def test_stage_notebook_map_matches_progress_model():
    for stage in PIPELINE_STAGES:
        assert STAGE_NOTEBOOK[stage["id"]] == stage["notebook"]


def test_every_stage_has_entry_point():
    for stage in PIPELINE_STAGES:
        assert stage["id"] in STAGE_ENTRY_POINTS


@pytest.mark.parametrize("filename", NUMBERED_NOTEBOOKS)
def test_numbered_notebooks_use_pipeline_modules(filename: str):
    source = _notebook_source(filename)
    assert "backend.services.pipeline" in source or "backend.notebook_utils" in source, (
        f"{filename} must import backend.services.pipeline or backend.notebook_utils"
    )


@pytest.mark.parametrize("filename", NUMBERED_NOTEBOOKS)
def test_numbered_notebooks_avoid_bypass_patterns(filename: str):
    source = _notebook_source(filename)
    for pattern, message in FORBIDDEN_NOTEBOOK_PATTERNS:
        assert not re.search(pattern, source), f"{filename}: {message}"


def test_offline_parse_match_matches_import_from_file_core(monkeypatch):
    """Notebook stages 03+04 ≡ import_from_file without live enrich."""
    monkeypatch.setenv("MCMASTER_BROWSE_RESOLVE_ENABLED", "0")
    monkeypatch.setenv("MCMASTER_API_ENABLED", "0")

    loaded = load_local_bom_file()
    assert loaded is not None
    content, name = loaded

    staged = offline_file_import_parts(content, name, include_match=True)
    parse_only = parse_bom_only(content, name)
    pipeline_matched = match_parts_only(parse_only)

    assert len(staged) == len(pipeline_matched)
    for a, b in zip(staged, pipeline_matched, strict=True):
        assert a.original_name == b.original_name
        assert a.mcmaster_url == b.mcmaster_url
        assert a.match_tier == b.match_tier
        assert a.mcmaster_status == b.mcmaster_status


@pytest.mark.asyncio
async def test_import_from_file_matches_offline_stages(monkeypatch):
    monkeypatch.setenv("MCMASTER_BROWSE_RESOLVE_ENABLED", "0")
    monkeypatch.setenv("MCMASTER_API_ENABLED", "0")

    loaded = load_local_bom_file()
    assert loaded is not None
    content, name = loaded

    project = await import_from_file(content, name)
    staged = offline_file_import_parts(content, name, include_match=True)

    assert len(project.parts) == len(staged)
    for api_part, staged_part in zip(project.parts, staged, strict=True):
        assert api_part.mcmaster_url == staged_part.mcmaster_url
        assert api_part.match_tier == staged_part.match_tier


def test_parts_from_scrape_result_file_branch_matches_parse_and_match():
    from backend.services.pipeline import parts_from_scrape_result
    from backend.services.scraper import ScrapeResult

    loaded = load_local_bom_file()
    assert loaded is not None
    content, name = loaded

    result = ScrapeResult(
        title="Test",
        description="",
        makerworld_url="https://makerworld.com/en/models/1",
        thumbnail_url="",
        bom_bytes=content,
        bom_filename=name,
        bom_content_type="text/csv",
        bom_source="file",
    )
    merged = parts_from_scrape_result(result)
    expected = offline_file_import_parts(content, name, include_match=True)
    assert len(merged) == len(expected)
    for a, b in zip(merged, expected, strict=True):
        assert a.mcmaster_url == b.mcmaster_url


def test_parts_from_scrape_result_embedded_branch():
    from backend.services.pipeline import parts_from_scrape_result
    from backend.services.scraper import ScrapeResult

    embedded = [
        Part(original_name="M3x8 socket head cap screw", specification=""),
    ]
    result = ScrapeResult(
        title="Test",
        description="",
        makerworld_url="https://makerworld.com/en/models/1",
        thumbnail_url="",
        bom_bytes=None,
        bom_filename=None,
        bom_content_type=None,
        bom_source="embedded",
        embedded_parts=embedded,
    )
    matched = parts_from_scrape_result(result)
    assert len(matched) == 1
    assert matched[0].match_tier in {"filtered_browse", "catalog", "category_search", "rule"}


def test_notebook_05_uses_safe_import_project():
    source = _notebook_source("05_api_payload.ipynb")
    assert "safe_import_project" in source
    assert "import_from_url" in source or "safe_import_project" in source
