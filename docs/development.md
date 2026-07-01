# Development

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm

## Initial setup

```bash
# Clone and enter the repo
cd makemcmasterBOM

# Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Frontend dependencies
cd frontend && npm install && cd ..
```

## Running dev services

```bash
./scripts/dev.sh
```

This starts three processes:

| Service | Port | URL |
|---------|------|-----|
| FastAPI (uvicorn) | 8000 | http://localhost:8000/api/health |
| Vite dev server | 5173 | http://localhost:5173 |
| JupyterLab | 8888 | http://localhost:5173/jupyter/lab/tree/notebooks |

Press `Ctrl+C` to stop all services.

### Cleanup and uninstall

| Script | Purpose |
|--------|---------|
| `./scripts/cleanup.sh` | Remove caches and build artifacts; keeps `.venv` and `node_modules` |
| `./scripts/cleanup.sh --deep` | Same as above, plus `.venv` and `frontend/node_modules` |
| `./scripts/uninstall.sh` | Full teardown (venv, node_modules, caches, notebook artifacts) |
| `./scripts/uninstall.sh --with-playwright` | Also remove `~/.cache/ms-playwright` (shared browser download) |

Both scripts stop dev servers on ports 8000, 8888, and 5173. Use `--dry-run` to preview deletions.

```bash
./scripts/cleanup.sh              # safe reset of caches
./scripts/uninstall.sh --yes      # remove everything local to this repo
```

### Running services individually

```bash
# API only
.venv/bin/uvicorn backend.main:app --reload --port 8000

# Frontend only
cd frontend && npm run dev

# JupyterLab only
.venv/bin/jupyter lab --no-browser --port=8888 --notebook-dir=.
```

## Environment variables

Set in `.env` at the repo root (loaded by `python-dotenv`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | off | Set to `1` for verbose logging, scrape metadata in SSE events, `/api/debug/logs`, and error tracebacks |
| `SCRAPER` | `auto` | `auto` = httpx then Playwright on 403/proxy errors; `playwright` = headless Chromium only; `httpx` = HTTP only |
| `RATE_LIMIT_ENABLED` | `1` | Enable API import rate limits and outbound MakerWorld throttling |
| `RATE_LIMIT_IMPORT_PER_MINUTE` | `12` | Max `POST /api/import*` requests per client IP per minute |
| `RATE_LIMIT_OUTBOUND_MIN_INTERVAL` | `1.0` | Minimum seconds between outbound MakerWorld HTTP requests |
| `RATE_LIMIT_MAX_CONCURRENT_SCRAPES` | `2` | Max simultaneous scrape/fetch operations |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed origins for FastAPI CORS |

### McMaster vendor settings

Optional McMaster enrichment (see [McMaster adapter](backend/mcmaster.md)):

| Variable | Default | Description |
|----------|---------|-------------|
| `MCMASTER_FILTERED_BROWSE_ENABLED` | `1` | Build filtered browse URLs (metric thread + length facets) when no catalog hit |
| `MCMASTER_BROWSE_RESOLVE_ENABLED` | `0` | Live Playwright browse table → part number (slow; integration only) |
| `MCMASTER_API_ENABLED` | `0` | Official McMaster Product Information API enrichment |
| `MCMASTER_API_USERNAME` | — | B2B API username (never commit) |
| `MCMASTER_API_PASSWORD` | — | B2B API password (never commit) |
| `MCMASTER_API_CERT_PATH` | — | Path to client PFX certificate |
| `MCMASTER_API_BASE_URL` | `https://api.mcmaster.com/v1` | API base URL |

Contact [eprocurement@mcmaster.com](mailto:eprocurement@mcmaster.com) for API access. See [official API docs](https://www.mcmaster.com/help/api/).

### Debug mode

```bash
./scripts/dev.sh --debug
```

Or set `DEBUG=1` in `.env` and restart the API.

When debug is on:

- FastAPI logs at DEBUG level
- `GET /api/health` includes `"debug": true` and `rate_limit` settings
- `GET /api/debug/logs` returns recent pipeline/scrape log entries
- Import SSE stage events include a `debug` object (URL, HTML size, BOM link, etc.)
- Import errors include tracebacks in the debug panel
- Click the bug icon in the app header to open the debug panel

### Rate limiting

Enabled by default (`RATE_LIMIT_ENABLED=1`). Protects against abuse and throttles outbound MakerWorld requests.

| Layer | Behavior |
|-------|----------|
| **API** | `POST /api/import*` limited per client IP (default 12/min) → HTTP 429 with `Retry-After` |
| **Outbound** | Min interval between MakerWorld fetches + max concurrent scrapes (see env vars above) |

`GET /api/import/stages` is not rate limited. Disable locally with `RATE_LIMIT_ENABLED=0`.

In development, the Vite proxy handles `/api` routing so CORS is typically not an issue.

## Notebook-driven workflow

1. Open a pipeline notebook in JupyterLab (via `/notebooks` page or directly)
2. Prototype and validate logic against sample data in `data/` or real MakerWorld URLs
3. When stable, promote functions into `backend/services/`
4. Update the notebook to import from the service module
5. Add or update tests in `tests/`
6. API routers should call service functions, not notebook code

See [Notebooks](notebooks.md) for the stage-to-module mapping.

## Building for production

```bash
# Build frontend
cd frontend && npm run build

# Serve API + static frontend
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

When `frontend/dist/` exists, FastAPI serves the built React app from `/`.

## Project skills

Cursor agent skills in `.cursor/skills/`:

| Skill | Purpose |
|-------|---------|
| `notebook-driven-pipeline` | Rules for notebook-first development |
| `promote-notebook-to-service` | Checklist for promoting notebook code to services |

## Common tasks

### Add a new column alias for BOM parsing

1. Edit `COLUMN_ALIASES` in `backend/services/parsers/spreadsheet/columns.py` (or prototype in `03_parse_bom.ipynb`)
2. Add a test case in `tests/test_parser_matcher.py`
3. Run `pytest`

### Improve McMaster matching

1. Experiment in `04_match_mcmaster.ipynb`
2. Update `data/mcmaster_catalog.json`, `matcher.py`, or `hardware_match_verify.py`
3. Run `pytest` and `scripts/check_hardware_specs.py --match`

### Tune MakerWorld scraping

1. Test against real URLs in `01_scrape.ipynb` (run `prepare_crawl_env()` first)
2. Update extraction in `backend/services/parsers/makerworld/` or attachment logic in `scraper.py`
3. If httpx returns 403, set `SCRAPER=playwright` or `SCRAPER=auto` (default)
4. See [PLAN.md](../PLAN.md) Phase 2 and [Scraper](backend/scraper.md)

### Parse BOM from a project description (no AI)

Many MakerWorld projects list hardware under headers like **Material required** or **BOM** in the description. Rule-based extraction runs automatically during import and merges with embedded/file BOMs.

```bash
# From a saved HTML/text file or stdin
./scripts/parse_description_bom.sh description.html

# Show candidate lines only
./scripts/parse_description_bom.sh --lines description.html

# From a live MakerWorld URL
./scripts/parse_description_bom.sh --url 'https://makerworld.com/en/models/...'
```

Implementation: `backend/services/parsers/makerworld/description.py` (keyword sections, quantity patterns, hardware signals). Legacy import: `backend.services.description_bom`.

Runtime checks:

```bash
./scripts/check_bom_quantities.py tests/fixtures/description_mega_python.txt
./scripts/check_hardware_specs.py --match parts.json   # after export or API dump
```

See [Parsers](backend/parsers.md) and [LIBRARY.md](../backend/services/parsers/LIBRARY.md) for module layout.

### Module import map

| Use case | Canonical import |
|----------|------------------|
| Description BOM | `from backend.services.parsers.makerworld.description import parts_from_description` |
| Embedded BOM | `from backend.services.parsers.makerworld import parts_from_design` |
| Spreadsheet BOM | `from backend.services.parsers.spreadsheet import parse_bom_bytes` |
| Hardware signals | `from backend.services.parsers.helpers.hardware_signals import has_hardware_signal` |
| McMaster match | `from backend.services.matcher import match_parts` |

Legacy shims (`description_bom`, `makerworld_bom`, `parser`, `hardware_terms`) remain for backward compatibility.
