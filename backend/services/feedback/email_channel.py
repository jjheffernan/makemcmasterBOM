"""SMTP email dispatch for match-error reports."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from backend import config
from backend.models.match_report import MatchErrorReport
from backend.services.feedback.formatters import report_plain_text, report_title

logger = logging.getLogger(__name__)


def _email_configured() -> bool:
    return bool(
        config.FEEDBACK_EMAIL_ENABLED
        and config.FEEDBACK_SMTP_HOST
        and config.FEEDBACK_EMAIL_TO
        and config.FEEDBACK_SMTP_FROM
    )


def _send_sync(report: MatchErrorReport) -> None:
    msg = EmailMessage()
    msg["Subject"] = report_title(report)
    msg["From"] = config.FEEDBACK_SMTP_FROM
    msg["To"] = config.FEEDBACK_EMAIL_TO
    if report.reporter_email:
        msg["Reply-To"] = report.reporter_email
    body = report_plain_text(report)
    msg.set_content(body)

    with smtplib.SMTP(config.FEEDBACK_SMTP_HOST, config.FEEDBACK_SMTP_PORT) as smtp:
        if config.FEEDBACK_SMTP_USE_TLS:
            smtp.starttls()
        if config.FEEDBACK_SMTP_USER:
            smtp.login(config.FEEDBACK_SMTP_USER, config.FEEDBACK_SMTP_PASSWORD)
        smtp.send_message(msg)


async def send_report_email(report: MatchErrorReport) -> tuple[bool, str]:
    if not _email_configured():
        return False, "email channel not configured"

    try:
        await asyncio.to_thread(_send_sync, report)
    except Exception as exc:
        logger.warning("Feedback email failed for %s: %s", report.id, exc)
        return False, str(exc)

    return True, f"sent to {config.FEEDBACK_EMAIL_TO}"
