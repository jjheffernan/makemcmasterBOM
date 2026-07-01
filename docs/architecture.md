# Architecture

## Goal

Accept a MakerWorld model URL, scrape the project BOM, and produce an editable hardware table with McMaster-Carr search links.

```
MakerWorld URL  →  Scrape  →  Parse BOM  →  Match McMaster  →  Editable table  →  CSV export
```

## Components

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (React + Vite)          http://localhost:5173         │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Import   │  │ BOM Editor   │  │ Notebooks (Jupyter iframe) │  │
│  └────┬─────┘  └──────┬───────┘  └────────────┬─────────────┘  │
│       │               │                        │                 │
│       └───────────────┴────── /api/* ──────────┘                 │
│                              │ proxy                             │
└──────────────────────────────┼───────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend (FastAPI)                http://localhost:8000         │
│  ┌────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Routers   │→ │  Pipeline   │→ │  Services               │  │
│  │  /import   │  │             │  │  scraper → parser →     │  │
│  │  /bom      │  │             │  │  matcher                │  │
│  │  /notebooks│  └─────────────┘  └─────────────────────────┘  │
│  │  /debug    │         │                  │                    │
│  └─────┬──────┘         │                  ▼                    │
│        │                │         page_fetch + parsers.makerworld  │
│        ▼                │         (httpx / Playwright)         │
│  ┌────────────┐         │                  │                    │
│  │ rate_limit │◄────────┴──────────────────┘                    │
│  │ (in+out)   │                                                  │
│  └─────┬──────┘                                                  │
│        ▼                                                         │
│  ┌────────────┐                                                  │
│  │ In-memory  │  (MVP — no database)                             │
│  │ store      │                                                  │
│  └────────────┘                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  JupyterLab                       http://localhost:8888         │
│  Proxied at /jupyter via Vite                                   │
│  notebooks/01_scrape.ipynb … 05_api_payload.ipynb               │
│  Same pipeline entry points as API (via notebook_utils)         │
└─────────────────────────────────────────────────────────────────┘
```

## Repository layout

```
makerworld-bom/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # DEBUG, rate-limit env vars
│   ├── rate_limit.py        # Inbound import limits + outbound throttling
│   ├── debug_log.py         # In-memory scrape/pipeline log buffer
│   ├── notebook_utils.py    # Jupyter-only helpers (not duplicated logic)
│   ├── api/
│   │   └── store.py         # In-memory project store
│   ├── models/
│   │   ├── part.py          # Part schema
│   │   ├── project.py       # Project schema (+ bom_status, warnings)
│   │   └── progress.py      # Pipeline stage events (SSE)
│   ├── routers/
│   │   ├── import_router.py # POST /api/import*, GET /stages
│   │   ├── bom_router.py    # GET/PUT /api/bom/{id}, export
│   │   ├── notebooks_router.py
│   │   └── debug_router.py  # /api/debug/* (when DEBUG=1)
│   └── services/
│       ├── scraper.py       # MakerWorld scrape orchestration
│       ├── page_fetch.py    # httpx + Playwright HTML fetch
│       ├── http_client.py   # Browser headers, error formatting
│       ├── matcher.py       # Part → McMaster URL + verification
│       ├── hardware_spec.py # Metric size/length extraction
│       ├── hardware_match_verify.py  # Post-match size/length checks
│       ├── mcmaster_catalog.py / mcmaster_handler.py
│       ├── vendors/         # Supplier adapters (McMaster first — see docs/backend/vendors.md)
│       │   └── mcmaster/    # tiers, filters, API, browse parse
│       ├── pipeline.py      # End-to-end orchestration + stage functions
│       ├── parsers/         # Site-specific BOM parsers (see LIBRARY.md)
│       │   ├── helpers/     # hardware_signals, bom_quantities, quantity_checks, …
│       │   ├── makerworld/  # description, embedded, page_json
│       │   └── spreadsheet/ # columns, csv_xlsx
│       ├── description_bom.py  # shim → parsers.makerworld.description
│       ├── makerworld_bom.py   # shim → parsers.makerworld.*
│       ├── parser.py           # shim → parsers.spreadsheet
│       └── hardware_terms.py   # shim → parsers.helpers.hardware_signals
├── frontend/
│   └── src/
│       ├── pages/           # Import, BOM editor, Notebooks
│       └── lib/api.ts       # Typed fetch wrappers
├── notebooks/               # Pipeline development notebooks
├── tests/                   # pytest suite
├── data/                    # Sample BOM files, regression_urls.json
└── docs/                    # This documentation
```

## Import pipeline

When a user submits a MakerWorld URL, the backend runs stages coordinated by `pipeline.import_from_url`:

1. **Validate** — normalize and validate the MakerWorld URL.
2. **Scrape** (`pipeline.scrape_makerworld` → `scraper.scrape_project`) — fetch HTML via `page_fetch` (rate-limited), extract metadata and BOM:
   - **Embedded BOM** — `parsers.makerworld.embedded` parses `__NEXT_DATA__` (`boms_v2`, filaments, other parts).
   - **Description BOM** — `parsers.makerworld.description` (rule-based prose / `Parts:` blocks).
   - **File BOM** — download CSV/XLSX attachment when present.
3. **Parse** (`parsers.spreadsheet.parse_bom_bytes`) — spreadsheet bytes → `Part` list (skipped when parts already embedded).
4. **Match** (`matcher.match_parts`) — tiered McMaster resolution (`vendors/mcmaster/tiers.py`): catalog → rules → part# → filtered browse → category search; then `hardware_match_verify` checks size/length. Optional API/browse enrichment when configured.
5. **Finalize** — assemble `Project` with `bom_status` and `warnings`.

If no BOM is found, the import returns **200** with `bom_status: "none"`, non-empty `warnings`, and an empty `parts` list.

Notebooks call the same stage functions (`scrape_makerworld`, `parse_bom_only`, `match_parts_only`, `import_from_url`) — see [Notebooks](notebooks.md).

## Rate limiting

`backend/rate_limit.py` protects two boundaries:

| Layer | What it limits | Default |
|-------|----------------|---------|
| **Inbound** | `POST /api/import*` per client IP | 12/min → HTTP 429 |
| **Outbound** | MakerWorld HTTP (httpx + Playwright + BOM download) | 1s min interval, 2 concurrent |

Disable locally with `RATE_LIMIT_ENABLED=0`. Config is exposed on `GET /api/health`.

## Design principles

- **Notebook-first development** — experimental logic starts in `notebooks/` before promotion to `backend/services/`.
- **Single pipeline** — notebooks and API share `pipeline.*` entry points; `notebook_utils.py` is Jupyter-only glue.
- **Preserve originals** — `original_name` keeps the BOM source value; `normalized_name` is used for search.
- **Search links + catalog SKUs** — tiered vendor adapter (`backend/services/vendors/`): curated catalog, filtered browse URLs, optional [official API](https://www.mcmaster.com/help/api/) enrichment.
- **Graceful missing BOM** — no hard failure when a project has no hardware list.
- **No persistence (MVP)** — projects live in `backend/api/store.py` until the server restarts. There is no database; do not assume cross-request durability outside explicit API responses.
- **Test isolation** — `tests/conftest.py` clears the in-memory store and rate limiter between tests so parallel runs do not leak BOM history.

## Network boundaries

All MakerWorld HTTP requests run **server-side** via `httpx` (with optional Playwright fallback). The browser never fetches MakerWorld directly (CORS would block it, and scraping logic would be exposed).

In development, the Vite dev server proxies:

| Path | Target |
|------|--------|
| `/api/*` | `http://127.0.0.1:8000` |
| `/jupyter/*` | `http://127.0.0.1:8888` |

In production, FastAPI can serve the built frontend from `frontend/dist/` on the same origin.
