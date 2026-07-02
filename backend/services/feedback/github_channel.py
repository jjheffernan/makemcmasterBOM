"""GitHub issue creation for match-error reports."""

from __future__ import annotations

import logging

import httpx

from backend import config
from backend.models.match_report import MatchErrorReport
from backend.services.feedback.formatters import report_markdown, report_title

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


def _github_configured() -> bool:
    return bool(
        config.FEEDBACK_GITHUB_ENABLED
        and config.FEEDBACK_GITHUB_TOKEN
        and config.FEEDBACK_GITHUB_REPO
        and "/" in config.FEEDBACK_GITHUB_REPO
    )


def _github_labels() -> list[str]:
    raw = config.FEEDBACK_GITHUB_LABELS.strip()
    if not raw:
        return ["bug", "match-report"]
    return [label.strip() for label in raw.split(",") if label.strip()]


async def create_github_issue(report: MatchErrorReport) -> tuple[bool, str, str]:
    """
    Create a GitHub issue for the report.

    Returns (ok, detail, issue_url).
    """
    if not _github_configured():
        return False, "github channel not configured", ""

    owner, repo = config.FEEDBACK_GITHUB_REPO.split("/", 1)
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {config.FEEDBACK_GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "title": report_title(report)[:256],
        "body": report_markdown(report),
        "labels": _github_labels(),
    }

    try:
        async with httpx.AsyncClient(timeout=config.FEEDBACK_WEBHOOK_TIMEOUT) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        logger.warning("GitHub issue creation failed for %s: %s", report.id, exc)
        return False, str(exc), ""

    issue_url = str(data.get("html_url", ""))
    issue_number = data.get("number")
    detail = f"issue #{issue_number}" if issue_number else "issue created"
    return True, detail, issue_url
