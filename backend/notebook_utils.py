"""Helpers for Jupyter pipeline notebooks — env setup, progress, offline fallbacks."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from typing import Any

from backend.models.part import Part
from backend.models.progress import PIPELINE_STAGES, StageEvent
from backend.notebook_frames import (
    BROWSE_ROW_COLUMNS,
    PART_COLUMNS,
    browse_rows_to_dataframe,
    alternatives_to_dataframe,
    parts_to_dataframe,
    project_parts_dataframe,
)
from backend.notebook_pipeline import format_pipeline_map, offline_file_import_parts
from backend.models.progress import PIPELINE_STAGES
from backend.services.pipeline import (
    import_from_url,
    match_parts_only,
    parse_bom_only,
    parts_from_scrape_result,
    scrape_makerworld,
)
from backend.services.scraper import ScrapeResult

_PROXY_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
REGRESSION_PATH = DATA_DIR / "regression_urls.json"
MCMASTER_REGRESSION_PATH = DATA_DIR / "mcmaster_regression_urls.json"
SAMPLE_BOM_PATH = DATA_DIR / "sample_bom.csv"
PARTS_CACHE_PATH = DATA_DIR / "notebook_parts.json"
SCRAPE_CACHE_PATH = DATA_DIR / "notebook_scrape.json"


def prepare_crawl_env(*, scraper: str = "auto", reload_backend: bool = True) -> None:
    """
    Prepare Jupyter for MakerWorld crawling.

    Same env as ./scripts/dev.sh: clears proxy vars, sets SCRAPER for page_fetch.
    """
    for key in _PROXY_KEYS:
        os.environ.pop(key, None)
    os.environ.setdefault("NO_PROXY", "*")
    os.environ["SCRAPER"] = scraper

    if reload_backend:
        import backend.services.http_client as http_client
        import backend.services.page_fetch as page_fetch
        import backend.services.pipeline as pipeline_mod
        import backend.services.scraper as scraper_mod

        importlib.reload(http_client)
        importlib.reload(page_fetch)
        importlib.reload(scraper_mod)
        importlib.reload(pipeline_mod)


def print_pipeline_map() -> None:
    """Show notebook ↔ API stage mapping (same as GET /api/import/stages)."""
    print(format_pipeline_map())


def notebook_progress(label: str = "notebook"):
    """Progress callback that prints stage events like the web import UI."""

    def on_progress(event: StageEvent) -> None:
        thumb = " 🖼" if event.thumbnail_url else ""
        print(f"[{label}] {event.stage:16} {event.status:8} {event.message}{thumb}")

    return on_progress


def load_regression_catalog(path: Path | None = None) -> dict[str, Any]:
    catalog_path = path or REGRESSION_PATH
    if not catalog_path.is_file():
        return {"urls": []}
    return json.loads(catalog_path.read_text())


def load_mcmaster_regression_catalog(path: Path | None = None) -> dict[str, Any]:
    """Curated McMaster browse / BOM cases for cross-test (see scripts/mcmaster_cross_test.py)."""
    from backend.services.vendors.mcmaster.cross_test import load_mcmaster_regression_catalog

    return load_mcmaster_regression_catalog(path or MCMASTER_REGRESSION_PATH)


def run_mcmaster_cross_test_offline() -> str:
    """Run offline matcher ↔ pipeline ↔ parser parity; returns text report."""
    from backend.services.vendors.mcmaster.cross_test import (
        format_cross_test_report,
        run_offline_cross_test,
    )

    return format_cross_test_report(run_offline_cross_test())


def pick_sample_url(
    *,
    index: int = 1,
    require_bom: bool = True,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    catalog = catalog or load_regression_catalog()
    urls: list[dict[str, Any]] = catalog.get("urls", [])
    if not urls:
        raise FileNotFoundError(
            f"No regression URLs in {REGRESSION_PATH}. Add curated MakerWorld links."
        )
    pool = [u for u in urls if u.get("expect_bom")] if require_bom else urls
    if not pool:
        pool = urls
    return pool[min(index, len(pool) - 1)]


async def safe_scrape(
    url: str,
    *,
    on_error: str = "skip",
    on_progress=None,
    timeout_s: float = 90.0,
) -> ScrapeResult | None:
    """`pipeline.scrape_makerworld` with notebook-friendly errors and a hard timeout."""
    import asyncio

    try:
        return await asyncio.wait_for(
            scrape_makerworld(url, on_progress=on_progress),
            timeout=timeout_s,
        )
    except TimeoutError:
        print(f"Crawl timed out after {timeout_s:g}s for {url}")
        print("  Hint: prepare_crawl_env(scraper='playwright') or increase timeout_s")
        if on_error == "raise":
            raise
        return None
    except Exception as exc:
        hint = (
            f"Crawl failed for {url}\n  {exc}\n"
            "  Try: prepare_crawl_env(scraper='playwright') and restart kernel."
        )
        print(hint)
        if on_error == "raise":
            raise
        return None


def load_local_bom_file(data_dir: Path | None = None) -> tuple[bytes, str] | None:
    data_dir = data_dir or DATA_DIR
    for pattern in ("*.csv", "*.xlsx", "*.xls"):
        for path in sorted(data_dir.glob(pattern)):
            return path.read_bytes(), path.name
    if SAMPLE_BOM_PATH.is_file():
        return SAMPLE_BOM_PATH.read_bytes(), SAMPLE_BOM_PATH.name
    return None


def load_cached_parts(data_dir: Path | None = None) -> list[Part] | None:
    path = (data_dir or DATA_DIR) / PARTS_CACHE_PATH.name
    if not path.is_file():
        return None
    try:
        return [Part.model_validate(item) for item in json.loads(path.read_text())]
    except Exception as exc:
        print(f"Could not read {path}: {exc}")
        return None


def cache_parts(parts: list[Part], data_dir: Path | None = None) -> Path:
    data_dir = data_dir or DATA_DIR
    data_dir.mkdir(exist_ok=True)
    path = data_dir / PARTS_CACHE_PATH.name
    path.write_text(json.dumps([p.model_dump() for p in parts], indent=2))
    return path


def cache_scrape_summary(result: ScrapeResult, data_dir: Path | None = None) -> Path:
    data_dir = data_dir or DATA_DIR
    data_dir.mkdir(exist_ok=True)
    path = data_dir / SCRAPE_CACHE_PATH.name
    path.write_text(
        json.dumps(
            {
                "title": result.title,
                "makerworld_url": result.makerworld_url,
                "bom_source": result.bom_source,
                "bom_filename": result.bom_filename,
                "embedded_part_count": len(result.embedded_parts),
                "warnings": result.warnings,
            },
            indent=2,
        )
    )
    return path


async def resolve_parts_offline(
    data_dir: Path | None = None,
) -> tuple[list[Part], str]:
    """Offline fallbacks only — not used by the live website."""
    data_dir = data_dir or DATA_DIR
    cached = load_cached_parts(data_dir)
    if cached:
        return cached, "cached notebook_parts.json"
    local = load_local_bom_file(data_dir)
    if local:
        content, filename = local
        try:
            parts = offline_file_import_parts(content, filename, include_match=False)
            if parts:
                cache_parts(parts, data_dir)
                return parts, f"local file {filename} (parse_bom_only)"
        except Exception as exc:
            print(f"Could not parse {filename}: {exc}")
    return [], "none"


async def safe_import_project(url: str, on_progress=None):
    """`pipeline.import_from_url` — identical to POST /api/import."""
    try:
        return await import_from_url(url, on_progress=on_progress)
    except Exception as exc:
        print(f"import_from_url failed:\n  {exc}\n  Using offline fallback…")
        from backend.models.project import Project

        parts, source = await resolve_parts_offline()
        if not parts:
            return None
        matched = match_parts_only(parts)
        return Project(
            title="Notebook fallback project",
            makerworld_url=url,
            description=f"Offline fallback ({source})",
            parts=matched,
            bom_status="upload",
            warnings=[
                "Live import failed — offline fallback only (no enrich_mcmaster stage)",
            ],
        )
