#!/usr/bin/env python3
"""Validate after-hours-loop state.json (schema version 1). Exit 1 on failure."""
from __future__ import annotations

import json
import sys

REQUIRED = (
    "version",
    "startedAt",
    "sources",
    "queue",
    "prs",
    "maxPrs",
    "tick",
    "priority",
    "baseBranch",
)
PRIORITIES = frozenset({"github-first", "fifo", "todo-first"})
STATUSES = frozenset({"open", "in-progress", "done", "blocked", "skipped"})
STOP_REASONS = frozenset({"done", "blocked", "noop", "budget"})
STOP_DETAILS = frozenset(
    {
        "empty-queue",
        "maxPrs",
        "guardrail",
        "user-stop",
        "consecutive-blocked",
        "ci-red",
        "preflight",
        "dry-run",
    }
)


def fail(msg: str) -> None:
    print(f"validate-state: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: validate-state.py <path-to-state.json>")
    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        fail(f"cannot read JSON: {e}")

    if not isinstance(data, dict):
        fail("root must be an object")
    if data.get("version") != 1:
        fail(f"version must be 1, got {data.get('version')!r}")
    for key in REQUIRED:
        if key not in data:
            fail(f"missing required key: {key}")

    priority = data["priority"]
    if not isinstance(priority, str) or priority not in PRIORITIES:
        fail(f"priority invalid: {priority!r}")

    prs = data["prs"]
    if not isinstance(prs, list):
        fail("prs must be a list")
    for i, pr in enumerate(prs):
        if not isinstance(pr, dict):
            fail(f"prs[{i}] must be an object")
        if "url" not in pr or not isinstance(pr["url"], str) or not pr["url"]:
            fail(f"prs[{i}] requires non-empty string url")

    queue = data["queue"]
    if not isinstance(queue, list):
        fail("queue must be a list")
    for i, item in enumerate(queue):
        if not isinstance(item, dict):
            fail(f"queue[{i}] must be an object")
        if "id" not in item or not isinstance(item["id"], str) or not item["id"]:
            fail(f"queue[{i}] requires non-empty string id")
        status = item.get("status")
        if status not in STATUSES:
            fail(f"queue[{i}].status invalid: {status!r}")

    if "consecutiveBlocked" in data:
        cb = data["consecutiveBlocked"]
        if not isinstance(cb, int) or isinstance(cb, bool) or cb < 0:
            fail("consecutiveBlocked must be a non-negative int")

    if "stopReason" in data and data["stopReason"] is not None:
        if data["stopReason"] not in STOP_REASONS:
            fail(f"stopReason invalid: {data['stopReason']!r}")

    if "stopDetail" in data and data["stopDetail"] is not None:
        detail = data["stopDetail"]
        if not isinstance(detail, str) or not detail:
            fail("stopDetail must be a non-empty string when set")
        if detail not in STOP_DETAILS:
            fail(f"stopDetail invalid: {detail!r}")

    if "megaPr" in data and data["megaPr"] is not None:
        if not isinstance(data["megaPr"], bool):
            fail("megaPr must be a boolean when set")

    print("ok")


if __name__ == "__main__":
    main()
