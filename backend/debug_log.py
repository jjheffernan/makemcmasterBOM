"""In-memory debug log (enabled when DEBUG=1)."""

from __future__ import annotations

import logging
from collections import deque
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from backend.config import DEBUG

logger = logging.getLogger("makerworld_bom")

_MAX_ENTRIES = 200
_entries: deque[dict[str, Any]] = deque(maxlen=_MAX_ENTRIES)
_lock = Lock()


def configure_logging() -> None:
    level = logging.DEBUG if DEBUG else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.setLevel(level)


def record(
    category: str,
    message: str,
    *,
    data: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "category": category,
        "message": message,
        "data": data or {},
    }
    if DEBUG:
        with _lock:
            _entries.append(entry)
        logger.debug("[%s] %s %s", category, message, data or "")
    return entry if DEBUG else None


def get_entries(limit: int = 100) -> list[dict[str, Any]]:
    with _lock:
        items = list(_entries)
    return items[-limit:]


def clear() -> None:
    with _lock:
        _entries.clear()
