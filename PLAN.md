# Execution plan

MakerWorld BOM → McMaster-Carr — delivery status and backlog.

**Current state (July 2026):** Phases 1–9 complete. MVP is usable end-to-end:
import MakerWorld BOM → match McMaster browse links → optional live hydration →
edit → export. Matcher covers **41** hardware categories with monthly taxonomy
refresh for Fastening & Joining.

---

## Phase 1 — Project setup ✅

FastAPI + React + JupyterLab via `./scripts/dev.sh` (API :8000, Vite :5173,
Jupyter :8888). Shared `backend` imports in notebooks.

## Phase 2 — MakerWorld ingestion ✅

Embedded `__NEXT_DATA__` BOM, description BOM, CSV/XLSX uploads, httpx →
Playwright fallback, rate limiting, debug mode, regression URLs.

## Phase 3 — BOM parsing ✅

Site parser layout (`parsers/`), column aliases, quantity/spec check scripts,
spreadsheet regression fixtures.

## Phase 4 — McMaster linking ✅

Catalog + category routes, filtered browse URLs, vendor adapter tiers, optional
API + browse resolve, confidence tiers, size/length verification.

## Phase 5 — Frontend MVP ✅

Import → BOM editor → export; warnings, debug panel, pricing tab, import
progress with enrich stage, match warnings, report-error UI.

## Phase 6 — Test & regression harness ✅

pytest suite (350+ offline), guardrails, `run_checks.sh`, query-accuracy
fixture, regression notebook, GitHub Actions CI.

## Phase 7 — McMaster browse (in-house) ✅

Migrated upstream mcmaster-scraper → `browse_scrape` / `browse_parse` /
`browse_fetch`. Cross-test fixtures. Archive:
`docs/archive/mcmaster-scraper-v0.2.1/`.

## Phase 8 — McMaster matcher maturity ✅

- [x] Nut and washer **subtype** routing (`nut_subtype`, `washer_subtype`)
- [x] **Imperial** fastener parsing + filtered browse facets
- [x] **Structured guesses** — same-size vs wider-scope alternatives (`guess_strategy`)
- [x] **Metacategories** — 26 McMaster nav departments (`mcmaster_metacategories.json`)
- [x] **Fastening & Joining** category expansion (41 matcher categories)
- [x] **Monthly taxonomy crawl** — polite batch job + PR workflow ([mcmaster-taxonomy.md](docs/backend/mcmaster-taxonomy.md))
- [x] Query-accuracy fixture (`bom_listing_query_cases.json`)
- [x] Exclude McMaster Standard Components from BOM matching

**Exit:** Offline matcher tests pass; category routes validated; taxonomy
refreshes monthly without per-import crawl load.

## Phase 9 — Feedback & BOM editor UX ✅

- [x] Match-error report persistence + optional dispatch (email / GitHub / webhook) — [feedback-dispatch.md](docs/backend/feedback-dispatch.md)
- [x] BOM **section headings** and drag-to-reorder within sections
- [x] **Hardware check** hint tooltips per fastener family
- [x] Grouped **match alternatives** in UI (guess scope labels)

---

## Phase 10 — Backlog

### McMaster matching

- [ ] Filtered browse roots for `hex_bolt`, `threaded_rod`, `set_screw` (currently category-search only)
- [ ] Expand matcher categories beyond Fastening (Power Transmission, Sealing, pipe fittings)
- [ ] Cross-check `hardware_spec.py` extractions against McMaster API `Specifications[]`
- [ ] Review monthly taxonomy PRs → promote high-value new families into `mcmaster_categories.json`

### Frontend & E2E

- [ ] Frontend component tests (Vitest / RTL)
- [ ] End-to-end browser import smoke (real URLs; keep `@integration` gated)

### Ops & integrations

- [ ] Live SMTP / GitHub dispatch smoke tests (mocked in CI today)
- [ ] Persistent project store (replace in-memory `api/store.py`) if multi-user needed

### Security (see [docs/security.md](docs/security.md))

- [ ] Strict hostname URL validation (McMaster + MakerWorld) — block SSRF / private IPs
- [ ] Rate-limit and cap `POST /api/bom/sync-pricing`
- [ ] Trusted-proxy handling for `X-Forwarded-For` rate-limit keys
- [ ] Upload size limits on `POST /api/import/file`
- [ ] `http(s)`-only external links in BOM editor (+ optional API validation on save)
- [ ] API authentication before any public deployment

### Docs & notebooks

- [x] Taxonomy + data file reference — [mcmaster-taxonomy.md](docs/backend/mcmaster-taxonomy.md), [data/README.md](data/README.md)
- [x] Security audit + [security.md](docs/security.md)
- [ ] Notebook refresh when Phase 10 matcher categories land

---

## Key references

| Area | Doc |
|------|-----|
| Architecture | [docs/architecture.md](docs/architecture.md) |
| McMaster adapter | [docs/backend/mcmaster.md](docs/backend/mcmaster.md) |
| Taxonomy & monthly crawl | [docs/backend/mcmaster-taxonomy.md](docs/backend/mcmaster-taxonomy.md) |
| Testing | [docs/testing.md](docs/testing.md) |
| Data files | [data/README.md](data/README.md) |
| Security | [docs/security.md](docs/security.md) |

**Archived planning notes:** [docs/archive/plan-history.md](docs/archive/plan-history.md) (superseded Phase 6 iteration list, tech stack audit table, original Phase 5 scope). Archive index: [docs/archive/README.md](docs/archive/README.md).
