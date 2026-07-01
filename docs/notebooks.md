# Notebooks

Pipeline notebooks exercise the **same `backend.services` modules** as the web app (`POST /api/import/stream`).

## Quick start

```bash
./scripts/dev.sh          # API + Jupyter
# or open http://localhost:5173/notebooks
```

In every notebook, **run cell 1 first**:

```python
from backend.notebook_utils import prepare_crawl_env
prepare_crawl_env(scraper="auto")  # or "playwright" if 403
```

## Pipeline map (notebooks = website)

| Stage | Notebook | Service entry point | API |
|-------|----------|---------------------|-----|
| `validate` + `scrape` | `01_scrape.ipynb` | `pipeline.scrape_makerworld` | import stream |
| `extract_bom` | `02_extract_bom.ipynb` | `scraper.scrape_project` (via above) | import stream |
| `parse_bom` | `03_parse_bom.ipynb` | `pipeline.parse_bom_only` | import stream |
| `match_mcmaster` | `04_match_mcmaster.ipynb` | `pipeline.match_parts_only` | import stream |
| `finalize` | `05_api_payload.ipynb` | `pipeline.import_from_url` | `POST /api/import` |
| `regression` | `06_regression.ipynb` | `scripts/run_checks.sh` | CI / manual QA |

**Optional McMaster browse workflow** (separate from MakerWorld pipeline):

| Stage | Notebook | Service entry point |
|-------|----------|---------------------|
| `browse` | `mcmaster_browse.ipynb` | `browse_fetch` + `browse_parse` |

`print_pipeline_map()` in a notebook prints the main pipeline table (from `PIPELINE_STAGES` in `backend/models/progress.py`).

## Step-by-step workflow

1. **01** — `safe_scrape(url)` → `ScrapeResult` (title, embedded parts, optional file bytes)
2. **02** — same scrape via `safe_scrape`; save `bom_bytes` to `data/` or cache embedded parts
3. **03** — `parse_bom_only(bytes, filename)` (→ `parse_upload_bytes`) for CSV/XLSX/JSON/MD/HTML/TXT; embedded BOMs skip parse (same as API)
4. **04** — `match_parts_only(parts)` → McMaster URLs, catalog SKUs, confidence, `hardware_match_status`; optional `check_bom_specifications`
5. **05** — `safe_import_project(url)` → full `Project` JSON (identical to website)
6. **06** — `scripts/run_checks.sh` + optional live regression URL crawl (`RUN_LIVE_SCRAPE`)

**Optional:** `mcmaster_browse.ipynb` — in-house browse scrape + fixture parse + cross-test (`data/mcmaster_regression_urls.json`)

## McMaster cross-test

Curated BOM lines and browse URLs live in `data/mcmaster_regression_urls.json`. The cross-test verifies matcher and pipeline agree:

| Path | Entry point | Same as website? |
|------|-------------|------------------|
| App matcher | `match_part()` | Yes — used after import |
| Notebook pipeline | `match_parts_only()` | Yes — `04_match_mcmaster.ipynb` |
| Live browse | `browse_fetch.fetch_browse_rows()` | Optional — Playwright when enabled |

```bash
python scripts/mcmaster_cross_test.py           # offline (CI / run_checks.sh)
python scripts/mcmaster_cross_test.py --live    # Playwright + SKU checks
```

In `mcmaster_browse.ipynb`: `run_mcmaster_cross_test_offline()` from `backend.notebook_utils`.

Upstream reference (if browse fetch fails): `docs/archive/mcmaster-scraper-v0.2.1/`

## Shared helpers (`backend/notebook_utils.py`)

| Helper | Purpose |
|--------|---------|
| `prepare_crawl_env()` | Proxy cleanup + module reload (Jupyter only) |
| `safe_scrape(url, timeout_s=90)` | `scrape_makerworld` with hard timeout and friendly errors |
| `safe_import_project(url)` | `import_from_url` with timeout + friendly errors |
| `notebook_progress()` | Prints stage events like the import UI |
| `pick_sample_url()` | Regression URL from `data/regression_urls.json` |
| `resolve_parts_offline()` | Fallback to cache / `sample_bom.csv` when crawl fails |
| `parts_to_dataframe()` | Structured BOM + match columns (`backend/notebook_frames.py`) |
| `browse_rows_to_dataframe()` | McMaster browse table rows as DataFrame |

### Parser imports in notebooks

Prefer canonical paths (see [Parsers](backend/parsers.md)):

```python
from backend.services.parsers.makerworld.description import parts_from_description
from backend.services.parsers.helpers.hardware_signals import has_hardware_signal
from backend.services.parsers.spreadsheet import parse_bom_bytes
```

Legacy shims (`description_bom`, `makerworld_bom`, `parser`, `hardware_terms`) still work.

Offline fallbacks are **notebook-only**; the website always runs the live pipeline.

Outbound MakerWorld requests share the same rate limiter as the API (`backend/rate_limit.py`). In Jupyter, use `prepare_crawl_env()` to clear proxy env vars that can break httpx/Playwright.

## Promotion workflow

Prototype in notebooks → promote to `backend/services/` → notebooks import the service (no duplicated logic).

See `.cursor/skills/promote-notebook-to-service/SKILL.md`.
