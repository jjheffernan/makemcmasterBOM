"""User-submitted reports when McMaster matching is wrong."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from backend.models.part import Part

ReportSide = Literal["mcmaster", "makerworld"]

McMasterIssueType = Literal[
    "wrong_part_number",
    "wrong_category_or_search",
    "missed_hardware",
    "wrong_finish_or_material",
    "should_be_not_applicable",
    "other",
]

MakerWorldIssueType = Literal[
    "makerworld_wrong_line",
    "makerworld_missing_hardware",
    "makerworld_wrong_quantity",
    "makerworld_parse_error",
    "makerworld_other",
]

MatchIssueType = McMasterIssueType | MakerWorldIssueType


class MatchErrorReportCreate(BaseModel):
    """Payload from the report-an-error form."""

    project_id: str = ""
    project_title: str = ""
    makerworld_url: str = ""
    report_side: ReportSide = "mcmaster"
    part_index: int | None = None
    part: Part | None = None
    issue_type: MatchIssueType
    message: str = Field(min_length=1, max_length=4000)
    expected_part_number: str = Field(default="", max_length=64)
    expected_url: str = Field(default="", max_length=2048)
    expected_finish: str = Field(default="", max_length=256)
    makerworld_line_text: str = Field(default="", max_length=1024)
    expected_line_text: str = Field(default="", max_length=1024)
    expected_quantity: float | None = Field(default=None, ge=0.0)
    parse_context: str = Field(default="", max_length=1024)
    page_url: str = Field(default="", max_length=2048)
    reporter_email: str = Field(default="", max_length=320)


class MatchErrorReport(MatchErrorReportCreate):
    """Stored report with server metadata."""

    id: str
    reported_at: str

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
