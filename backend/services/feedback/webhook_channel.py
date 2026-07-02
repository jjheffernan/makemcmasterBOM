"""Generic webhook dispatch (Discord, Matrix bridges, Slack, etc.)."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

from backend import config
from backend.models.match_report import MatchErrorReport
from backend.services.feedback.formatters import (
    discord_embed_payload,
    webhook_payload,
)

logger = logging.getLogger(__name__)


def _webhook_urls() -> list[str]:
    raw = config.FEEDBACK_WEBHOOK_URLS.strip()
    if not raw:
        return []
    return [url.strip() for url in raw.split(",") if url.strip()]


def _is_discord_webhook(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return host.endswith("discord.com") or host.endswith("discordapp.com")


def _payload_for_url(
    report: MatchErrorReport,
    url: str,
    *,
    github_issue_url: str = "",
) -> dict:
    if _is_discord_webhook(url):
        return discord_embed_payload(report, github_issue_url=github_issue_url)
    return webhook_payload(report, github_issue_url=github_issue_url)


async def post_report_webhooks(
    report: MatchErrorReport,
    *,
    github_issue_url: str = "",
) -> list[tuple[str, bool, str]]:
    """
    POST the report to each configured webhook URL.

    Returns a list of (url_host, ok, detail) tuples.
    """
    if not config.FEEDBACK_WEBHOOK_ENABLED:
        return []

    urls = _webhook_urls()
    if not urls:
        return []

    results: list[tuple[str, bool, str]] = []
    async with httpx.AsyncClient(timeout=config.FEEDBACK_WEBHOOK_TIMEOUT) as client:
        for url in urls:
            host = urlparse(url).netloc or url
            payload = _payload_for_url(report, url, github_issue_url=github_issue_url)
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                results.append((host, True, f"HTTP {response.status_code}"))
            except Exception as exc:
                logger.warning("Webhook failed for %s (%s): %s", report.id, host, exc)
                results.append((host, False, str(exc)))
    return results
