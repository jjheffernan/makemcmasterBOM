"""In-memory project store for MVP (no persistence across server restarts)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from backend.models.project import Project, ProjectHistoryItem

MAX_HISTORY = 5

_store: dict[str, Project] = {}
_history: list[str] = []
_timestamps: dict[str, dict[str, str]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _touch_history(project_id: str) -> None:
    if project_id in _history:
        _history.remove(project_id)
    _history.insert(0, project_id)
    while len(_history) > MAX_HISTORY:
        evicted = _history.pop()
        _store.pop(evicted, None)
        _timestamps.pop(evicted, None)


def save(project: Project) -> str:
    project_id = str(uuid.uuid4())
    now = _now_iso()
    _store[project_id] = project
    _timestamps[project_id] = {"imported_at": now, "updated_at": now}
    _touch_history(project_id)
    return project_id


def get(project_id: str) -> Project | None:
    return _store.get(project_id)


def update(project_id: str, project: Project) -> bool:
    if project_id not in _store:
        return False
    _store[project_id] = project
    meta = _timestamps.setdefault(
        project_id,
        {"imported_at": _now_iso(), "updated_at": _now_iso()},
    )
    meta["updated_at"] = _now_iso()
    _touch_history(project_id)
    return True


def list_history(*, limit: int = MAX_HISTORY) -> list[ProjectHistoryItem]:
    items: list[ProjectHistoryItem] = []
    for project_id in _history[:limit]:
        project = _store.get(project_id)
        meta = _timestamps.get(project_id)
        if not project or not meta:
            continue
        items.append(
            ProjectHistoryItem(
                project_id=project_id,
                title=project.title or "Untitled BOM",
                thumbnail_url=project.thumbnail_url,
                makerworld_url=project.makerworld_url,
                parts_count=len(project.parts),
                bom_status=project.bom_status,
                imported_at=meta["imported_at"],
                updated_at=meta["updated_at"],
            )
        )
    return items


def clear_all() -> None:
    """Reset store — for tests only."""
    _store.clear()
    _history.clear()
    _timestamps.clear()
