"""Tests for match-error feedback API."""

from __future__ import annotations

import json

import pytest

from backend.api import feedback_store
from backend.models.part import Part


@pytest.fixture(autouse=True)
def isolated_match_reports(tmp_path, monkeypatch):
    path = tmp_path / "match_reports.jsonl"
    monkeypatch.setenv("MATCH_REPORTS_PATH", str(path))
    yield
    feedback_store.clear_reports()


@pytest.mark.asyncio
async def test_submit_match_error_report(api_client):
    part = Part(
        original_name="M3x8 Socket Head Cap Screw",
        specification="Stainless",
        mcmaster_part_number="91290A115",
        match_tier="catalog",
        confidence=0.95,
    )
    response = await api_client.post(
        "/api/feedback/match-error",
        json={
            "project_id": "",
            "issue_type": "wrong_part_number",
            "message": "Should be 91290A120 for 16 mm length",
            "part": part.model_dump(),
            "expected_part_number": "91290A120",
            "page_url": "http://localhost:5173/bom/abc123?tab=parts",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"]
    assert body["reported_at"]

    stored = feedback_store.list_reports()
    assert len(stored) == 1
    assert stored[0].issue_type == "wrong_part_number"
    assert stored[0].expected_part_number == "91290A120"
    assert stored[0].part.original_name == "M3x8 Socket Head Cap Screw"
    assert stored[0].page_url == "http://localhost:5173/bom/abc123?tab=parts"


@pytest.mark.asyncio
async def test_submit_match_error_enriches_from_project(api_client):
    import_response = await api_client.post(
        "/api/import/file",
        files={"file": ("bom.csv", b"Qty,Part Name\n1,M3 bolt\n", "text/csv")},
    )
    project_id = import_response.json()["project_id"]

    response = await api_client.post(
        "/api/feedback/match-error",
        json={
            "project_id": project_id,
            "part_index": 0,
            "issue_type": "wrong_category_or_search",
            "message": "Linked to wrong screw family",
        },
    )
    assert response.status_code == 200

    stored = feedback_store.list_reports()[0]
    assert stored.project_id == project_id
    assert stored.part is not None
    assert stored.part.original_name == "M3 bolt"


@pytest.mark.asyncio
async def test_submit_makerworld_report(api_client):
    response = await api_client.post(
        "/api/feedback/match-error",
        json={
            "report_side": "makerworld",
            "issue_type": "makerworld_wrong_quantity",
            "message": "MakerWorld lists 2 but the design needs 8",
            "makerworld_url": "https://makerworld.com/en/models/123",
            "expected_quantity": 8,
            "page_url": "http://localhost:5173/bom/test",
        },
    )
    assert response.status_code == 200

    stored = feedback_store.list_reports()[0]
    assert stored.report_side == "makerworld"
    assert stored.issue_type == "makerworld_wrong_quantity"
    assert stored.expected_quantity == 8
    assert stored.makerworld_url == "https://makerworld.com/en/models/123"


@pytest.mark.asyncio
async def test_submit_match_error_rejects_empty_message(api_client):
    response = await api_client.post(
        "/api/feedback/match-error",
        json={
            "issue_type": "other",
            "message": "   ",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_match_report_persisted_as_jsonl(api_client, tmp_path, monkeypatch):
    path = tmp_path / "reports.jsonl"
    monkeypatch.setenv("MATCH_REPORTS_PATH", str(path))

    await api_client.post(
        "/api/feedback/match-error",
        json={
            "issue_type": "missed_hardware",
            "message": "Bearing line was skipped",
        },
    )

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["issue_type"] == "missed_hardware"
    assert record["message"] == "Bearing line was skipped"
