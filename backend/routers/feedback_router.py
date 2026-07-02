"""User feedback when BOM → McMaster matching is wrong."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.api import store
from backend.api.feedback_store import append_report
from backend.models.match_report import MatchErrorReport, MatchErrorReportCreate
from backend.rate_limit import check_feedback_rate_limit
from backend.services.feedback.dispatcher import (
    DispatchChannelResult,
    dispatch_match_report,
)

router = APIRouter(prefix="/feedback", tags=["feedback"])


class MatchErrorReportResponse(BaseModel):
    id: str
    reported_at: str
    message: str = "Thank you — your report was saved."
    dispatch: list[DispatchChannelResult] = Field(default_factory=list)


@router.post("/match-error", response_model=MatchErrorReportResponse)
async def submit_match_error_report(
    request: Request,
    body: MatchErrorReportCreate,
) -> MatchErrorReportResponse:
    """
    Save a user report when hardware matching picked the wrong McMaster link.

    Reports append to ``data/match_reports.jsonl``. When ``FEEDBACK_DISPATCH_ENABLED``
    is set, the server also emails, opens a GitHub issue, and/or posts webhooks.
    """
    await check_feedback_rate_limit(request)

    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Please describe what went wrong.")

    payload = body.model_copy(update={"message": message})

    if payload.project_id:
        project = store.get(payload.project_id)
        if project:
            payload = payload.model_copy(
                update={
                    "project_title": payload.project_title or project.title,
                    "makerworld_url": payload.makerworld_url or project.makerworld_url,
                }
            )
            if payload.part_index is not None and payload.part is None:
                if 0 <= payload.part_index < len(project.parts):
                    payload = payload.model_copy(
                        update={"part": project.parts[payload.part_index]}
                    )

    report: MatchErrorReport = append_report(payload)
    dispatch_result = await dispatch_match_report(report)

    response_message = "Thank you — your report was saved."
    if dispatch_result.any_ok:
        response_message += " We've notified the maintainers."

    return MatchErrorReportResponse(
        id=report.id,
        reported_at=report.reported_at,
        message=response_message,
        dispatch=dispatch_result.channels,
    )
