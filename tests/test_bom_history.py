"""Tests for in-memory BOM history."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api import store
from backend.main import app
from backend.models.project import Project


@pytest.fixture(autouse=True)
def _clear_store():
    store.clear_all()
    yield
    store.clear_all()


def test_history_lists_recent_imports_newest_first():
    ids = []
    for i in range(3):
        ids.append(store.save(Project(title=f"Project {i}", parts=[])))

    history = store.list_history()
    assert [item.project_id for item in history] == list(reversed(ids))
    assert history[0].title == "Project 2"


def test_history_caps_at_five_and_evicts_oldest():
    first_id = store.save(Project(title="BOM 0", parts=[]))
    for i in range(1, 7):
        store.save(Project(title=f"BOM {i}", parts=[]))

    history = store.list_history()
    assert len(history) == 5
    assert history[0].title == "BOM 6"
    assert history[-1].title == "BOM 2"
    assert store.get(first_id) is None


def test_update_bumps_history_entry():
    pid = store.save(Project(title="Alpha", parts=[]))
    store.save(Project(title="Beta", parts=[]))
    store.update(pid, Project(title="Alpha edited", parts=[]))

    history = store.list_history()
    assert history[0].project_id == pid
    assert history[0].title == "Alpha edited"


@pytest.mark.asyncio
async def test_api_bom_history_endpoint():
    store.save(Project(title="API Test", parts=[], bom_status="upload"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/bom/history")

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 5
    assert len(body["items"]) == 1
    assert body["items"][0]["title"] == "API Test"
