# Archived execution plan notes

Summary of planning content removed from root `PLAN.md` after Phases 8–9
landed (July 2026). Kept for historical context only — **do not treat as
active backlog**.

## Phase 6 iteration loop (original)

The original Phase 6 framed open iteration work. All listed items are now
**done**:

| Original item | Resolution |
|---------------|------------|
| Regression URL list | `data/regression_urls.json` + `06_regression.ipynb` |
| Parser/matcher/API/scraper tests | 350+ pytest cases; CI in `.github/workflows/test.yml` |
| Guardrail tests | `tests/test_guardrails.py`, `scripts/run_checks.sh` |
| UI polish (resize, bulk edit) | BOM editor: column resize, row select, bulk qty/delete |
| Spreadsheet regression | `tests/test_spreadsheet_regression.py` |

Further test gaps moved to **Phase 10 backlog** in current `PLAN.md`.

## Phase 5 “scaffolded” (original)

Phase 5 was marked “scaffolded” with basic import/edit/export only. Since
completed:

- McMaster pricing tab with pack-aware totals
- Import progress + `enrich_mcmaster` hydration stage
- Match warnings, finish dropdowns, verify banners
- Report-error flow with category-specific forms
- BOM section headings and drag-to-reorder
- Hardware check hint tooltips (`?` per family)

## Tech stack audit (July 2026)

Decisions applied during MVP build:

| Finding | Action taken |
|---------|--------------|
| Missing `uvicorn`, `openpyxl`, `lxml`, `tenacity` | Added to `pyproject.toml` |
| Missing `@tanstack/react-query` | Added for API state |
| Jupyter not in product UI | `/notebooks` page + Vite `/jupyter` proxy |
| Dev orchestration | `scripts/dev.sh` (no Docker for local) |
| CORS in dev | Vite proxy to `/api` |
| MakerWorld blocks bot User-Agent | Browser headers in `http_client.py` |
| BOM is JSON in page, not CSV links | `parsers/makerworld/` parses `__NEXT_DATA__` |
| Parser layout | `backend/services/parsers/` — site packages + `helpers/` |
| Legacy imports | Shims: `description_bom`, `makerworld_bom`, `parser`, `hardware_terms` |
| Playwright for edge cases | `[playwright]` extra + `SCRAPER=auto` |
| Notebook vs API logic drift | Shared `pipeline.*`; `safe_scrape` / `safe_import_project` |
| In-memory store (no DB) | `backend/api/store.py`; test isolation via `conftest` |
| Credential / secret leaks | `tests/test_guardrails.py` + tracked-file scan |
| BOM field drift (qty, spec) | `check_bom_*` scripts + `test_regression_checks.py` |
| Catalog SKU drift | `check_catalog_integrity.py`; M3 16 mm → `91290A120` |
| McMaster vendor adapter | `backend/services/vendors/mcmaster/` |
| Multi-format file upload | `parsers/upload/` |
| Agent notebook stalls | `01_scrape.ipynb` uses `safe_scrape(timeout_s=90)` |
| Abuse / MakerWorld politeness | `rate_limit.py` |
| Hard-to-debug scrape failures | `DEBUG=1`, debug panel, `/api/debug/logs` |

## Cursor skills (still active)

- `.cursor/skills/notebook-driven-pipeline/` — notebook-first workflow
- `.cursor/skills/promote-notebook-to-service/` — promotion checklist
