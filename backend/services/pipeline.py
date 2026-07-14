"""Orchestrates scrape → parse → match pipeline."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from backend.models.part import Part
from backend.models.progress import ProgressCallback, StageEvent
from backend.models.project import Project
from backend.services.description_bom import merge_parts
from backend.services import matcher, parser, scraper
from backend.services.parsers.helpers.spec_metadata import normalize_part_specification

from backend.services.parsers.upload.dispatch import (
    ALLOWED_UPLOAD_EXTENSIONS,
    format_hint_for_extension,
)

ALLOWED_BOM_EXTENSIONS = ALLOWED_UPLOAD_EXTENSIONS


def _emit(
    on_progress: ProgressCallback | None,
    stage: StageEvent,
) -> None:
    if on_progress:
        on_progress(stage)


def _normalize_parsed_parts(parts: list) -> list:
    return [normalize_part_specification(p) for p in parts]


async def _maybe_enrich_parts(
    parts: list,
    on_progress: ProgressCallback | None = None,
) -> list:
    from backend import config

    if not (config.MCMASTER_API_ENABLED or config.MCMASTER_BROWSE_RESOLVE_ENABLED):
        _emit(
            on_progress,
            StageEvent(
                stage="enrich_mcmaster",
                status="skipped",
                message="Live McMaster hydration disabled",
            ),
        )
        return parts
    from backend.services.vendors.mcmaster.enrichment import enrich_parts

    return await enrich_parts(parts, on_progress=on_progress)


def _parse_and_match(
    content: bytes,
    filename: str,
    on_progress: ProgressCallback | None,
) -> list:
    _emit(
        on_progress,
        StageEvent(
            stage="parse_bom",
            status="running",
            message=f"Reading {filename}…",
        ),
    )
    try:
        parts = parser.parse_bom_bytes(content, filename)
    except Exception as exc:
        _emit(
            on_progress,
            StageEvent(
                stage="parse_bom",
                status="error",
                message=f"Could not parse BOM: {exc}",
            ),
        )
        raise

    if not parts:
        _emit(
            on_progress,
            StageEvent(
                stage="parse_bom",
                status="error",
                message="No parts found in the BOM file",
            ),
        )
        raise ValueError("No parts found in the BOM file")

    parts = _normalize_parsed_parts(parts)

    _emit(
        on_progress,
        StageEvent(
            stage="parse_bom",
            status="done",
            message=f"Found {len(parts)} parts",
        ),
    )

    _emit(
        on_progress,
        StageEvent(
            stage="match_mcmaster",
            status="running",
            message="Ranking McMaster-Carr browse links…",
        ),
    )
    parts = matcher.match_parts(parts)
    na_count = sum(1 for p in parts if p.mcmaster_status == "not_applicable")
    match_msg = f"Matched {len(parts)} parts"
    if na_count:
        match_msg += f" ({na_count} not on McMaster-Carr)"
    _emit(
        on_progress,
        StageEvent(
            stage="match_mcmaster",
            status="done",
            message=match_msg,
        ),
    )
    return parts


def _finalize_project(
    project: Project,
    on_progress: ProgressCallback | None,
) -> Project:
    _emit(
        on_progress,
        StageEvent(stage="finalize", status="running", message="Preparing editor…"),
    )
    _emit(
        on_progress,
        StageEvent(stage="finalize", status="done", message="Ready to edit"),
    )
    return project


async def import_from_file(
    content: bytes,
    filename: str,
    *,
    title: str = "",
    on_progress: ProgressCallback | None = None,
) -> Project:
    suffix = Path(filename).suffix.lower()
    _emit(
        on_progress,
        StageEvent(stage="validate", status="running", message="Checking file…"),
    )
    if suffix not in ALLOWED_BOM_EXTENSIONS:
        msg = format_hint_for_extension(suffix)
        _emit(
            on_progress,
            StageEvent(stage="validate", status="error", message=msg),
        )
        raise ValueError(msg)
    _emit(
        on_progress,
        StageEvent(stage="validate", status="done", message="File type OK"),
    )
    _emit(
        on_progress,
        StageEvent(
            stage="scrape",
            status="skipped",
            message="Skipped — BOM uploaded directly",
        ),
    )
    _emit(
        on_progress,
        StageEvent(
            stage="extract_bom",
            status="done",
            message=f"Using uploaded file {filename}",
        ),
    )

    parts = _parse_and_match(content, filename, on_progress)
    parts = await _maybe_enrich_parts(parts, on_progress)
    project = Project(
        title=title or Path(filename).stem.replace("_", " ").replace("-", " "),
        makerworld_url="",
        description=f"Uploaded BOM: {filename}",
        parts=parts,
        bom_status="upload",
    )
    return _finalize_project(project, on_progress)


async def scrape_makerworld(
    url: str,
    on_progress: ProgressCallback | None = None,
) -> scraper.ScrapeResult:
    """Validate URL and scrape project page — used by API and notebooks 01–02."""
    _emit(
        on_progress,
        StageEvent(stage="validate", status="running", message="Checking URL…"),
    )
    try:
        normalized = scraper.normalize_makerworld_url(url)
    except ValueError as exc:
        _emit(
            on_progress,
            StageEvent(stage="validate", status="error", message=str(exc)),
        )
        raise
    _emit(
        on_progress,
        StageEvent(stage="validate", status="done", message="URL looks valid"),
    )
    _emit(
        on_progress,
        StageEvent(
            stage="scrape",
            status="running",
            message="Downloading MakerWorld project page…",
        ),
    )
    try:
        return await scraper.scrape_project(
            normalized,
            on_progress=on_progress,
            skip_validate=True,
        )
    except Exception as exc:
        _emit(
            on_progress,
            StageEvent(stage="scrape", status="error", message=str(exc)),
        )
        raise


def parse_bom_only(
    content: bytes,
    filename: str,
    on_progress: ProgressCallback | None = None,
) -> list:
    """Parse spreadsheet BOM — notebook 03 / pipeline parse stage (no matching)."""
    _emit(
        on_progress,
        StageEvent(
            stage="parse_bom",
            status="running",
            message=f"Reading {filename}…",
        ),
    )
    try:
        parts = parser.parse_bom_bytes(content, filename)
    except Exception as exc:
        _emit(
            on_progress,
            StageEvent(
                stage="parse_bom",
                status="error",
                message=f"Could not parse BOM: {exc}",
            ),
        )
        raise

    if not parts:
        _emit(
            on_progress,
            StageEvent(
                stage="parse_bom",
                status="error",
                message="No parts found in the BOM file",
            ),
        )
        raise ValueError("No parts found in the BOM file")

    _emit(
        on_progress,
        StageEvent(
            stage="parse_bom",
            status="done",
            message=f"Found {len(parts)} parts",
        ),
    )
    return _normalize_parsed_parts(parts)


def match_parts_only(
    parts: list,
    on_progress: ProgressCallback | None = None,
) -> list:
    """McMaster matching — notebook 04 / pipeline match stage."""
    _emit(
        on_progress,
        StageEvent(
            stage="match_mcmaster",
            status="running",
            message="Ranking McMaster-Carr browse links…",
        ),
    )
    matched = matcher.match_parts(parts)
    na_count = sum(1 for p in matched if p.mcmaster_status == "not_applicable")
    match_msg = f"Matched {len(matched)} parts"
    if na_count:
        match_msg += f" ({na_count} not on McMaster-Carr)"
    _emit(
        on_progress,
        StageEvent(stage="match_mcmaster", status="done", message=match_msg),
    )
    return matched


def parts_from_scrape_result(
    result: scraper.ScrapeResult,
    on_progress: ProgressCallback | None = None,
) -> list:
    """Parse + match BOM from scrape result — same branching as `import_from_url`."""
    if result.bom_bytes and result.bom_filename:
        file_parts = _parse_and_match(
            result.bom_bytes, result.bom_filename, on_progress
        )
        if result.embedded_parts:
            embedded_matched = match_parts_only(
                result.embedded_parts, on_progress
            )
            return merge_parts(file_parts, embedded_matched)
        return file_parts
    if result.embedded_parts:
        _emit(
            on_progress,
            StageEvent(
                stage="parse_bom",
                status="skipped",
                message="Using MakerWorld embedded BOM (no spreadsheet file)",
            ),
        )
        return match_parts_only(result.embedded_parts, on_progress)
    _emit(
        on_progress,
        StageEvent(
            stage="parse_bom",
            status="skipped",
            message="No BOM on this project — skipping parse",
        ),
    )
    _emit(
        on_progress,
        StageEvent(
            stage="match_mcmaster",
            status="skipped",
            message="No parts to match",
        ),
    )
    return []


async def import_from_url(
    url: str,
    on_progress: ProgressCallback | None = None,
) -> Project:
    try:
        result = await scrape_makerworld(url, on_progress=on_progress)
    except Exception:
        raise

    warnings: list[str] = list(result.warnings)
    parts = parts_from_scrape_result(result, on_progress)
    parts = await _maybe_enrich_parts(parts, on_progress)

    project = Project(
        title=result.title,
        makerworld_url=result.makerworld_url,
        description=result.description,
        thumbnail_url=result.thumbnail_url,
        parts=parts,
        bom_status=result.bom_source,
        warnings=warnings,
    )
    return _finalize_project(project, on_progress)


def _parts_dataframe(parts: list) -> pd.DataFrame:
    rows = [p.model_dump() if hasattr(p, "model_dump") else p for p in parts]
    return pd.DataFrame(rows)


def _excel_cell(value: object) -> object:
    """openpyxl only accepts scalars — stringify nested Part fields."""
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def parts_to_csv(parts: list) -> str:
    buffer = io.StringIO()
    _parts_dataframe(parts).to_csv(buffer, index=False)
    return buffer.getvalue()


def parts_to_tsv(parts: list) -> str:
    buffer = io.StringIO()
    _parts_dataframe(parts).to_csv(buffer, index=False, sep="\t")
    return buffer.getvalue()


def parts_to_xlsx(parts: list) -> bytes:
    df = _parts_dataframe(parts)
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(_excel_cell)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()
