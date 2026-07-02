"""Canonical notebook ↔ website pipeline mapping.

Notebooks must call into `backend.services.pipeline` (via `notebook_utils`
wrappers) — never duplicate parse/match/scrape logic inline. This module is
the single source of truth for stage ownership and is validated in tests.
"""

from __future__ import annotations

from pathlib import Path

from backend.models.progress import PIPELINE_STAGES, StageId

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"

# Primary pipeline entry point per import-progress stage (website + notebooks).
STAGE_ENTRY_POINTS: dict[StageId, str] = {
    "validate": "backend.services.pipeline.scrape_makerworld",
    "scrape": "backend.services.pipeline.scrape_makerworld",
    "extract_bom": "backend.services.scraper.scrape_project",
    "parse_bom": "backend.services.pipeline.parse_bom_only",
    "match_mcmaster": "backend.services.pipeline.match_parts_only",
    "enrich_mcmaster": "backend.services.vendors.mcmaster.enrichment.enrich_parts",
    "finalize": "backend.services.pipeline.import_from_url",
}

# Notebook that owns each stage (matches PIPELINE_STAGES after sync check).
STAGE_NOTEBOOK: dict[StageId, str] = {
    stage["id"]: stage["notebook"]  # type: ignore[misc]
    for stage in PIPELINE_STAGES
}

# Optional / auxiliary notebooks (not in the 7-stage import progress bar).
AUXILIARY_NOTEBOOKS: dict[str, dict[str, str]] = {
    "06_regression.ipynb": {
        "title": "06 — Regression checks",
        "description": "Offline validators, spreadsheet fixtures, optional live MakerWorld crawl.",
        "stage": "regression",
        "entry": "scripts/run_checks.sh",
    },
    "mcmaster_browse.ipynb": {
        "title": "McMaster browse (optional)",
        "description": "In-house browse fetch, fixture parse, and cross-test.",
        "stage": "browse",
        "entry": "backend.services.vendors.mcmaster.cross_test",
    },
}

# Numbered pipeline notebooks (01–05) must import these modules — not bypass them.
REQUIRED_PIPELINE_IMPORTS: tuple[str, ...] = (
    "backend.services.pipeline",
    "backend.notebook_utils",
)

# Patterns that indicate logic drift in numbered pipeline notebooks.
FORBIDDEN_NOTEBOOK_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"parse_bom_bytes\s*\(", "use pipeline.parse_bom_only instead of parser.parse_bom_bytes"),
    (r"scraper\.scrape_project\s*\(", "use pipeline.scrape_makerworld or safe_scrape"),
    (
        r"from backend\.services\.matcher import match_parts\b",
        "use pipeline.match_parts_only instead of matcher.match_parts",
    ),
    (
        r"matcher\.match_parts\s*\(",
        "use pipeline.match_parts_only instead of matcher.match_parts",
    ),
)


def pipeline_stage_rows() -> list[dict[str, str]]:
    """Same rows as GET /api/import/stages."""
    return list(PIPELINE_STAGES)


def notebook_path_for_stage(stage_id: StageId) -> Path:
    return NOTEBOOKS_DIR / STAGE_NOTEBOOK[stage_id]


def validate_pipeline_notebook_sync() -> list[str]:
    """Return human-readable sync errors (empty when notebooks match the API pipeline)."""
    errors: list[str] = []

    seen_notebooks: dict[str, list[str]] = {}
    for stage in PIPELINE_STAGES:
        nb = stage["notebook"]
        seen_notebooks.setdefault(nb, []).append(stage["id"])
        path = NOTEBOOKS_DIR / nb
        if not path.is_file():
            errors.append(f"Missing notebook for stage {stage['id']!r}: {path}")

    for nb, stages in seen_notebooks.items():
        if nb.startswith("0") and "enrich_mcmaster" in stages and nb != "05_api_payload.ipynb":
            errors.append(
                f"enrich_mcmaster should map to 05_api_payload.ipynb (full import), "
                f"not {nb}"
            )

    for filename in (
        "01_scrape.ipynb",
        "02_extract_bom.ipynb",
        "03_parse_bom.ipynb",
        "04_match_mcmaster.ipynb",
        "05_api_payload.ipynb",
    ):
        path = NOTEBOOKS_DIR / filename
        if not path.is_file():
            errors.append(f"Missing core pipeline notebook: {path}")

    return errors


def format_pipeline_map() -> str:
    """Text map for notebooks and docs."""
    lines = [
        "Pipeline stages (notebooks = website import progress):",
        "",
    ]
    for stage in PIPELINE_STAGES:
        entry = STAGE_ENTRY_POINTS.get(stage["id"], "?")
        lines.append(
            f"  [{stage['id']:16}] {stage['notebook']:22}  {stage['label']}"
        )
        lines.append(f"      → {entry}")
    lines.append("")
    lines.append("Website: POST /api/import/stream → backend.services.pipeline.import_from_url")
    lines.append("Notebooks 01–04: stage functions via backend.notebook_utils")
    lines.append("Notebook 05: import_from_url (identical to the website)")
    return "\n".join(lines)


def offline_file_import_parts(
    content: bytes,
    filename: str,
    *,
    include_match: bool = True,
) -> list:
    """
    Offline stages 03+04 — same path as import_from_file before enrich.

    Uses pipeline.parse_bom_only + match_parts_only (not raw parser/matcher).
    """
    from backend.services.pipeline import match_parts_only, parse_bom_only

    parts = parse_bom_only(content, filename)
    if include_match:
        return match_parts_only(parts)
    return parts
