"""Orchestrate outbound feedback dispatch after local persistence."""

from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, Field

from backend import config
from backend.models.match_report import MatchErrorReport
from backend.services.feedback.email_channel import send_report_email
from backend.services.feedback.github_channel import create_github_issue
from backend.services.feedback.webhook_channel import post_report_webhooks

logger = logging.getLogger(__name__)

DispatchChannel = Literal["email", "github", "webhook"]


class DispatchChannelResult(BaseModel):
    channel: DispatchChannel
    ok: bool
    detail: str = ""
    url: str = ""


class FeedbackDispatchResult(BaseModel):
    enabled: bool = False
    channels: list[DispatchChannelResult] = Field(default_factory=list)

    @property
    def any_ok(self) -> bool:
        return any(channel.ok for channel in self.channels)


async def dispatch_match_report(report: MatchErrorReport) -> FeedbackDispatchResult:
    """
    Fan out a stored report to configured outbound channels.

    Local JSONL persistence happens before this is called. Channel failures are
    logged and returned in ``channels`` but do not fail the API request.
    """
    if not config.FEEDBACK_DISPATCH_ENABLED:
        return FeedbackDispatchResult(enabled=False)

    results: list[DispatchChannelResult] = []
    github_issue_url = ""

    if config.FEEDBACK_GITHUB_ENABLED:
        ok, detail, issue_url = await create_github_issue(report)
        github_issue_url = issue_url
        results.append(
            DispatchChannelResult(
                channel="github",
                ok=ok,
                detail=detail,
                url=issue_url,
            )
        )

    if config.FEEDBACK_EMAIL_ENABLED:
        ok, detail = await send_report_email(report)
        results.append(DispatchChannelResult(channel="email", ok=ok, detail=detail))

    if config.FEEDBACK_WEBHOOK_ENABLED:
        webhook_results = await post_report_webhooks(
            report,
            github_issue_url=github_issue_url,
        )
        for host, ok, detail in webhook_results:
            results.append(
                DispatchChannelResult(
                    channel="webhook",
                    ok=ok,
                    detail=f"{host}: {detail}",
                )
            )

    if not results:
        logger.debug(
            "Feedback dispatch enabled but no channels configured for report %s",
            report.id,
        )

    return FeedbackDispatchResult(enabled=True, channels=results)
