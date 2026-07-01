"""Notebook discovery and JupyterLab integration."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/notebooks", tags=["notebooks"])

NOTEBOOKS_DIR = Path(__file__).resolve().parents[2] / "notebooks"

NOTEBOOK_META: dict[str, dict[str, str]] = {
    "01_scrape.ipynb": {
        "title": "01 — Scrape MakerWorld",
        "description": "Download project page, extract metadata, locate BOM attachment.",
        "stage": "scrape",
    },
    "02_extract_bom.ipynb": {
        "title": "02 — Extract BOM",
        "description": "Locate and download the BOM file from a scraped project.",
        "stage": "extract",
    },
    "03_parse_bom.ipynb": {
        "title": "03 — Parse BOM",
        "description": "Read CSV/XLSX into a DataFrame and normalize columns.",
        "stage": "parse",
    },
    "04_match_mcmaster.ipynb": {
        "title": "04 — Match McMaster",
        "description": "Generate McMaster-Carr search URLs and confidence scores.",
        "stage": "match",
    },
    "05_api_payload.ipynb": {
        "title": "05 — API Payload",
        "description": "Assemble the final Project/Part payload for the API.",
        "stage": "export",
    },
    "06_regression.ipynb": {
        "title": "06 — Regression checks",
        "description": "Offline validators, spreadsheet fixtures, optional live MakerWorld URL crawl.",
        "stage": "regression",
    },
    "mcmaster_browse.ipynb": {
        "title": "McMaster browse (optional)",
        "description": "In-house Playwright browse fetch, fixture parse, and cross-test.",
        "stage": "browse",
    },
}


class NotebookInfo(BaseModel):
    filename: str
    title: str
    description: str
    stage: str
    jupyter_path: str


class NotebooksResponse(BaseModel):
    notebooks: list[NotebookInfo]
    jupyter_url: str


def _notebook_meta(relative_path: str, filename: str) -> dict[str, str]:
    return NOTEBOOK_META.get(relative_path) or NOTEBOOK_META.get(filename, {})


@router.get("", response_model=NotebooksResponse)
async def list_notebooks() -> NotebooksResponse:
    notebooks: list[NotebookInfo] = []

    if NOTEBOOKS_DIR.exists():
        for path in sorted(NOTEBOOKS_DIR.glob("*.ipynb")):
            rel = path.relative_to(NOTEBOOKS_DIR).as_posix()
            meta = _notebook_meta(rel, path.name)
            notebooks.append(
                NotebookInfo(
                    filename=rel,
                    title=meta.get("title", path.stem),
                    description=meta.get(
                        "description", "Pipeline development notebook"
                    ),
                    stage=meta.get("stage", "dev"),
                    jupyter_path=f"notebooks/{rel}",
                )
            )

    return NotebooksResponse(
        notebooks=notebooks,
        jupyter_url="/jupyter/lab/tree/notebooks",
    )
