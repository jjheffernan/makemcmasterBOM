# Execution plan

Phased delivery for the MakerWorld BOM → McMaster-Carr MVP.

## Phase 1 — Project setup ✅

- [x] Repository scaffolded with `backend/`, `frontend/`, `notebooks/`, `tests/`, `data/`
- [x] FastAPI app with health, import, BOM, notebooks endpoints
- [x] React + Tailwind + shadcn-style components + TanStack Table
- [x] JupyterLab via `./scripts/dev.sh`, proxied at `/jupyter`
- [x] Notebooks page in web UI with embedded JupyterLab iframe
- [x] Shared Python venv imports `backend` modules from notebooks

**Exit:** `./scripts/dev.sh` runs API (:8000), Vite (:5173), JupyterLab (:8888).

## Phase 2 — MakerWorld ingestion ✅

- [x] Browser-like HTTP headers (fixes MakerWorld 403)
- [x] Parse embedded BOM from `__NEXT_DATA__` via `parsers/makerworld/embedded.py`
- [x] Rule-based BOM extraction from project descriptions via `parsers/makerworld/description.py`
- [x] CSV/XLSX anchor + JSON attachment fallback for uploaded BOMs
- [x] httpx → Playwright fallback via `SCRAPER=auto|httpx|playwright` + `pip install -e '.[playwright]'`
- [x] Missing BOM returns 200 with `bom_status: "none"` and `warnings` (no hard failure)
- [x] Regression URL list in `data/regression_urls.json`
- [x] Fixture + unit tests in `tests/test_makerworld_bom.py`; live test marked `@integration`
- [x] Notebooks call the same `pipeline.*` entry points as the API (no duplicated scrape logic)
- [x] Rate limiting: per-IP import limits + outbound MakerWorld throttling (`backend/rate_limit.py`)
- [x] Debug mode: `DEBUG=1` / `./scripts/dev.sh --debug` — logs, SSE metadata, debug panel

**Exit:** `POST /api/import` extracts BOM for MakerWorld projects with embedded BOM (808247, 574923) or description BOM (972938 Mega Python).

## Phase 3 — BOM parsing ✅

- [x] Site-specific parser layout (`backend/services/parsers/`) — see `LIBRARY.md`
- [x] Expanded column alias map (item name, product, sku, #)
- [x] Quantity + hardware spec runtime check scripts
- [x] Regression tests with captured MakerWorld CSV/XLSX exports (`tests/fixtures/makerworld_export_bom.csv`)
- [x] Support XLSX variants in `03_parse_bom.ipynb` (see `tests/test_spreadsheet_regression.py`)

**Exit:** API returns normalized `Part` list from uploaded spreadsheets.

## Phase 4 — McMaster linking ✅

- [x] Curated catalog (`data/mcmaster_catalog.json`) + category routes (`data/mcmaster_categories.json`)
- [x] Product URL pattern for catalog hits (`/{partNumber}/?searchQuery=…`, confidence 1.0)
- [x] Post-match size/length verification (`hardware_spec.py`, `hardware_match_verify.py`)
- [x] Filtered browse URLs + vendor adapter (`backend/services/vendors/mcmaster/`)
- [x] Optional official API client + browse `ProductPresentations` parser (in-house)
- [x] Document low-confidence rows in UI (verify banner + row highlight + match tier)
- [x] Tune confidence scoring thresholds for search-only rows (`resolve_match_status` + tier hints)

**Exit:** Every hardware row has a clickable McMaster search link.

## Phase 5 — Frontend MVP ✅ (scaffolded)

- [x] Import page with URL input and loading state
- [x] BOM editor with editable fields, delete, export CSV
- [x] Confidence display and external McMaster links
- [x] Import warnings banner when BOM missing
- [x] Debug panel (bug icon in header when `DEBUG=1`)

**Exit:** Full URL → edit → export workflow.

## Phase 6 — Iteration loop

- [x] Regression URL list (`data/regression_urls.json`)
- [x] Unit tests: parser/matcher, API, scraper, MakerWorld BOM, rate limits, debug, notebook utils
- [x] Guardrail tests (credential leaks, tracked secrets, CLI regression checks) + GitHub Actions CI
- [x] Regression notebook with curated MakerWorld links (`06_regression.ipynb`)
- [x] Parser/matcher unit tests expanded (captured export fixtures in `test_spreadsheet_regression.py`)
- [x] UI polish (column resize, bulk edit — row select, set quantity, delete selected)

## Phase 7 — McMaster browse (in-house) ✅

- [x] Upstream [mcmaster-scraper](https://github.com/thedjchi/mcmaster-scraper) v0.2.1 analyzed and migrated
- [x] In-house Playwright scrape (`browse_scrape.py`) + parse (`browse_parse.py`) + fetch gate (`browse_fetch.py`)
- [x] Cross-test (`data/mcmaster_regression_urls.json`, `scripts/mcmaster_cross_test.py`)
- [x] Archive reference at `docs/archive/mcmaster-scraper-v0.2.1/` (upstream sanity check)
- [x] Optional browse notebook (`notebooks/mcmaster_browse.ipynb`)
- [x] `vendor/` directory removed from repo

---

## Tech stack audit (applied)

| Finding | Action taken |
|---------|--------------|
| Missing `uvicorn`, `openpyxl`, `lxml`, `tenacity` | Added to `pyproject.toml` |
| Missing `@tanstack/react-query` | Added for API state |
| Jupyter not in product UI (user requested) | `/notebooks` page + Vite `/jupyter` proxy |
| Dev orchestration | `scripts/dev.sh` (no Docker for local) |
| CORS in dev | Vite proxy to `/api` — no CORS needed locally |
| MakerWorld blocks bot User-Agent | Browser headers in `http_client.py` |
| BOM is JSON in page, not CSV links | `parsers/makerworld/` parses `__NEXT_DATA__` |
| Parser layout | `backend/services/parsers/` — site packages + `helpers/`; see `LIBRARY.md` |
| Legacy imports | `description_bom`, `makerworld_bom`, `parser`, `hardware_terms` shims remain |
| Playwright for edge cases | `[playwright]` extra + `SCRAPER=auto` (httpx then browser) |
| Notebook vs API logic drift | Shared `pipeline.*` entry points; notebooks use `safe_scrape` / `safe_import_project` wrappers |
| In-memory store (no DB) | `backend/api/store.py`; tests isolate via `conftest._isolated_store` |
| Credential / secret leaks | `tests/test_guardrails.py` + tracked-file scan |
| BOM field drift (qty, spec) | `check_bom_quantities.py`, `check_bom_specifications.py`, `test_regression_checks.py` |
| Catalog SKU drift | `check_catalog_integrity.py`, M3 16 mm → `91290A120` (live-verified) |
| McMaster vendor adapter | `backend/services/vendors/mcmaster/` — tiers, filtered browse, API client, browse parse |
| Multi-format file upload | `parsers/upload/` — CSV, TSV, XLSX, JSON, MD, HTML, TXT |
| Agent notebook stalls | `01_scrape.ipynb` uses `safe_scrape(timeout_s=90)`; agents edit via JSON, not kernel run |
| Abuse / MakerWorld politeness | `rate_limit.py` — inbound 429 + outbound interval/concurrency |
| Hard-to-debug scrape failures | `DEBUG=1`, `debug_log.py`, `/api/debug/logs`, frontend debug panel |

## Skills created

- `.cursor/skills/notebook-driven-pipeline/` — notebook-first workflow
- `.cursor/skills/promote-notebook-to-service/` — promotion checklist
