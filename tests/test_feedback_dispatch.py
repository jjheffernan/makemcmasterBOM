"""Tests for feedback dispatch channels."""

from __future__ import annotations

import pytest

from backend.api import feedback_store
from backend.models.match_report import MatchErrorReport, MatchErrorReportCreate
from backend.services.feedback.dispatcher import dispatch_match_report
from backend.services.feedback.formatters import (
    discord_embed_payload,
    report_markdown,
    report_title,
    webhook_payload,
)


@pytest.fixture(autouse=True)
def isolated_match_reports(tmp_path, monkeypatch):
    path = tmp_path / "match_reports.jsonl"
    monkeypatch.setenv("MATCH_REPORTS_PATH", str(path))
    yield
    feedback_store.clear_reports()


def _sample_report() -> MatchErrorReport:
    payload = MatchErrorReportCreate(
        issue_type="wrong_part_number",
        message="Should be 91290A120 for 16 mm length",
        expected_part_number="91290A120",
        page_url="http://localhost:5173/bom/test",
        reporter_email="reporter@example.com",
    )
    return MatchErrorReport(
        id="report-test-1",
        reported_at="2026-07-01T12:00:00+00:00",
        **payload.model_dump(),
    )


def test_report_title_and_markdown():
    report = _sample_report()
    assert "McMaster report" in report_title(report)
    body = report_markdown(report)
    assert "91290A120" in body
    assert "reporter@example.com" in body


def test_webhook_payload_shape():
    report = _sample_report()
    payload = webhook_payload(report, github_issue_url="https://github.com/o/r/issues/1")
    assert payload["event"] == "match_error_report"
    assert payload["github_issue_url"].endswith("/issues/1")


def test_discord_embed_payload():
    report = _sample_report()
    payload = discord_embed_payload(report)
    assert payload["embeds"][0]["title"]


@pytest.mark.asyncio
async def test_dispatch_disabled_by_default(monkeypatch):
    monkeypatch.setenv("FEEDBACK_DISPATCH_ENABLED", "0")
    from backend import config

    config.FEEDBACK_DISPATCH_ENABLED = False

    result = await dispatch_match_report(_sample_report())
    assert result.enabled is False
    assert result.channels == []


@pytest.mark.asyncio
async def test_dispatch_github_and_webhook(monkeypatch, httpx_mock):
    from backend import config

    monkeypatch.setenv("FEEDBACK_DISPATCH_ENABLED", "1")
    config.FEEDBACK_DISPATCH_ENABLED = True
    config.FEEDBACK_GITHUB_ENABLED = True
    config.FEEDBACK_GITHUB_TOKEN = "ghp_test"
    config.FEEDBACK_GITHUB_REPO = "owner/repo"
    config.FEEDBACK_WEBHOOK_ENABLED = True
    config.FEEDBACK_WEBHOOK_URLS = "https://discord.com/api/webhooks/1/token"
    config.FEEDBACK_EMAIL_ENABLED = False

    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/issues",
        json={"number": 42, "html_url": "https://github.com/owner/repo/issues/42"},
    )
    httpx_mock.add_response(url="https://discord.com/api/webhooks/1/token")

    result = await dispatch_match_report(_sample_report())
    assert result.enabled is True
    assert result.any_ok
    channels = {item.channel: item for item in result.channels}
    assert channels["github"].ok is True
    assert channels["github"].url.endswith("/issues/42")
    assert channels["webhook"].ok is True


@pytest.mark.asyncio
async def test_api_returns_dispatch_metadata(api_client, monkeypatch, httpx_mock):
    from backend import config

    monkeypatch.setenv("FEEDBACK_DISPATCH_ENABLED", "1")
    config.FEEDBACK_DISPATCH_ENABLED = True
    config.FEEDBACK_GITHUB_ENABLED = True
    config.FEEDBACK_GITHUB_TOKEN = "ghp_test"
    config.FEEDBACK_GITHUB_REPO = "owner/repo"
    config.FEEDBACK_EMAIL_ENABLED = False
    config.FEEDBACK_WEBHOOK_ENABLED = False

    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/issues",
        json={"number": 7, "html_url": "https://github.com/owner/repo/issues/7"},
    )

    response = await api_client.post(
        "/api/feedback/match-error",
        json={
            "issue_type": "other",
            "message": "Test dispatch metadata",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dispatch"]
    assert body["dispatch"][0]["channel"] == "github"
    assert body["dispatch"][0]["ok"] is True
