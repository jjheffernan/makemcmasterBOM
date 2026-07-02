"""Notebook discovery and JupyterLab integration."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.models.progress import PIPELINE_STAGES
from backend.notebook_pipeline import AUXILIARY_NOTEBOOKS, NOTEBOOKS_DIR

router = APIRouter(prefix="/notebooks", tags=["notebooks"])

_STAGE_BY_NOTEBOOK: dict[str, str] = {}
for _stage in PIPELINE_STAGES:
    _STAGE_BY_NOTEBOOK.setdefault(_stage["notebook"], _stage["id"])

NOTEBOOK_META: dict[str, dict[str, str]] = {}
for _stage in PIPELINE_STAGES:
    nb = _stage["notebook"]
    if nb not in NOTEBOOK_META:
        NOTEBOOK_META[nb] = {
            "title": f"{nb[:2]} — {_stage['label']}",
            "description": _stage["description"],
            "stage": _stage["id"],
        }
NOTEBOOK_META.update(AUXILIARY_NOTEBOOKS)


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
