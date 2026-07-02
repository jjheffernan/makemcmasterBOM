---
name: notebook-driven-pipeline
description: >-
  Guides notebook-first development for the MakerWorld BOM pipeline. Use when
  prototyping scrapers, parsers, or McMaster matchers in notebooks/, promoting
  code to backend/services/, or validating pipeline stages before API exposure.
---

# Notebook-Driven Pipeline Development

## Workflow

1. Prototype in the numbered notebook for that stage (`notebooks/01_scrape.ipynb` … `05_api_payload.ipynb`)
2. Validate against sample data in `data/` or real MakerWorld URLs
3. Promote stable functions into `backend/services/`
4. Import promoted modules from notebooks to stay in sync
5. Expose via FastAPI routers only after notebook exit criteria pass

## Stage ownership

| Notebook | Service module | Exit criteria |
|----------|----------------|---------------|
| `01_scrape.ipynb` | `scraper.py` | Title, description, BOM link extracted |
| `02_extract_bom.ipynb` | `scraper.py` + `parsers/makerworld/` | BOM file saved to `data/` or description parts parsed |
| `03_parse_bom.ipynb` | `parsers/spreadsheet/` | Clean `Part` list from CSV/XLSX |
| `04_match_mcmaster.ipynb` | `matcher.py` + `hardware_match_verify.py` | McMaster URL + confidence per part |
| `05_api_payload.ipynb` | `pipeline.py` + `enrichment.py` | Full `Project` JSON payload incl. live hydrate |
| `06_regression.ipynb` | `scripts/run_checks.sh` | Offline validators + optional live URL crawl |
| `mcmaster_browse.ipynb` | `scripts/mcmaster_cross_test.py` | McMaster cross-test + optional live browse |

## Rules

- Do not edit service modules for experimental logic — notebook first
- **Promoted code only:** notebooks `01`–`05` call `backend.services.pipeline` (see `backend/notebook_pipeline.py`); parity is enforced by `tests/test_notebook_pipeline_parity.py`
- Preserve original BOM values in `original_name`; normalize into `normalized_name`
- Favor **size-filtered browse URLs** (metric or imperial thread/length facets) as the primary guess; catalog SKUs and category browse are structured secondaries (`guess_scope`: `same_size` vs `wider_scope`)
- Use `safe_scrape` / `safe_import_project` in notebooks (not bare `scrape_makerworld`) to avoid agent/kernel hangs
- MakerWorld HTTP calls stay server-side only (never browser fetch)

## Access

- Web UI: `/notebooks` in the React app
- JupyterLab: `./scripts/dev.sh` → http://localhost:5173/jupyter/lab/tree/notebooks
