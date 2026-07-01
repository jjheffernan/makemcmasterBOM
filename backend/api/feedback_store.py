"""Append-only store for user match-error reports (JSONL on disk)."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from backend.models.match_report import MatchErrorReport, MatchErrorReportCreate

REPO_ROOT = Path(__file__).resolve().parents[2]


def reports_path() -> Path:
    override = os.environ.get("MATCH_REPORTS_PATH")
    if override:
        return Path(override)
    return REPO_ROOT / "data" / "match_reports.jsonl"


def append_report(payload: MatchErrorReportCreate) -> MatchErrorReport:
    report = MatchErrorReport(
        id=str(uuid.uuid4()),
        reported_at=MatchErrorReport.now_iso(),
        **payload.model_dump(),
    )
    path = reports_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report.model_dump(), ensure_ascii=False) + "\n")
    return report


def list_reports(*, limit: int = 100) -> list[MatchErrorReport]:
    path = reports_path()
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    reports: list[MatchErrorReport] = []
    for line in lines[-limit:]:
        if not line.strip():
            continue
        reports.append(MatchErrorReport.model_validate(json.loads(line)))
    return reports


def clear_reports() -> None:
    """Remove all stored reports — tests only."""
    path = reports_path()
    if path.is_file():
        path.unlink()
