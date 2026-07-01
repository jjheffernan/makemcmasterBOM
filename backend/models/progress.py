from __future__ import annotations

from typing import Callable, Literal

from pydantic import BaseModel

StageId = Literal[
    "validate",
    "scrape",
    "extract_bom",
    "parse_bom",
    "match_mcmaster",
    "finalize",
]

StageStatus = Literal["pending", "running", "done", "error", "skipped"]

PIPELINE_STAGES: list[dict[str, str]] = [
    {
        "id": "validate",
        "notebook": "01_scrape.ipynb",
        "label": "Validate URL",
        "description": "Confirm this is a MakerWorld project link",
    },
    {
        "id": "scrape",
        "notebook": "01_scrape.ipynb",
        "label": "Scrape project page",
        "description": "Download the project page and read title & description",
    },
    {
        "id": "extract_bom",
        "notebook": "02_extract_bom.ipynb",
        "label": "Extract BOM file",
        "description": "Locate and download the bill of materials attachment",
    },
    {
        "id": "parse_bom",
        "notebook": "03_parse_bom.ipynb",
        "label": "Parse BOM",
        "description": "Read spreadsheet rows into structured parts",
    },
    {
        "id": "match_mcmaster",
        "notebook": "04_match_mcmaster.ipynb",
        "label": "Match McMaster-Carr",
        "description": "Generate search links and confidence scores",
    },
    {
        "id": "finalize",
        "notebook": "05_api_payload.ipynb",
        "label": "Prepare results",
        "description": "Assemble the editable BOM for the editor",
    },
]


class StageEvent(BaseModel):
    stage: StageId
    status: StageStatus
    message: str
    thumbnail_url: str | None = None
    debug: dict | None = None


ProgressCallback = Callable[[StageEvent], None]
