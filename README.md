# MakerWorld BOM → McMaster-Carr Generator

Lightweight web app that accepts a MakerWorld model URL, scrapes the project BOM, and generates an editable hardware table with McMaster-Carr search links.

## Quick start

```bash
# Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,playwright]"
playwright install chromium   # one-time, for MakerWorld scraping

# Frontend
cd frontend && npm install && cd ..

# Run all dev services (API + Vite + JupyterLab)
./scripts/dev.sh
```

- **App**: http://localhost:5173
- **API**: http://localhost:8000/api/health
- **JupyterLab**: http://localhost:5173/jupyter/lab/tree/notebooks

Optional: `./scripts/dev.sh --debug` for verbose logging and the in-app debug panel.

## Cleanup

```bash
./scripts/cleanup.sh           # caches and build output (keeps venv + node_modules)
./scripts/uninstall.sh --yes   # full local uninstall
```

See [Development guide — Cleanup and uninstall](docs/development.md#cleanup-and-uninstall) for options (`--deep`, `--with-playwright`, `--dry-run`).

## Development workflow

1. Prototype logic in `notebooks/` (same pipeline code as the API — see [docs/notebooks.md](docs/notebooks.md))
2. Promote stable code into `backend/services/`
3. Expose via FastAPI routers
4. Connect frontend screens

## Stack

| Layer | Tools |
|-------|-------|
| Backend | FastAPI, Pydantic, httpx, Playwright (optional), BeautifulSoup, pandas |
| Frontend | React, shadcn/ui, Tailwind CSS, TanStack Table |
| Dev | JupyterLab, pytest |

## Project structure

```
notebooks/     Pipeline development notebooks (shared entry points with API)
backend/       FastAPI app, services, models, routers, rate limiting
frontend/      React UI
tests/         pytest suite (unit + optional live integration)
data/          McMaster routing JSON, taxonomy crawl output — see data/README.md
docs/          Documentation (start at docs/README.md)
.github/       CI: tests on push/PR; monthly McMaster taxonomy crawl
```

## Documentation

Full documentation lives in [`docs/`](docs/README.md):

- [Architecture](docs/architecture.md) — system overview, pipeline, rate limiting
- [API reference](docs/api.md) — HTTP endpoints (import, BOM, feedback, pricing sync)
- [Backend services](docs/backend/scraper.md) — scraper, parser, matcher, pipeline
- [McMaster taxonomy](docs/backend/mcmaster-taxonomy.md) — category data + monthly crawl
- [Security](docs/security.md) — threat model and deployment checklist
- [Development guide](docs/development.md) — setup, env vars, debug mode
- [Data files](data/README.md) — routing JSON reference
- [Execution plan](PLAN.md) — phased delivery status and backlog
