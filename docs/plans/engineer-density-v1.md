# Engineer-density v1 — after-hours feature plan

**Goal:** Make MakerWorld BOM → McMaster matching feel like a power tool McMaster engineers would respect: dense, fast, preference-driven, rigorously tested.

**Base:** `dev` · **Budget:** `/after-hours 30m` · **maxPrs:** 12 · **Beyond budget:** leave uncommitted work on latest relevant `after-hours/*` or `dev`.

**Rules:** Prefer worktrees + agents. Large installs / new OAuth or PDF stacks → **Later (deps review)** only. Do not invent product scope overnight.

---

## Kickoff Sources (this run)

```text
/after-hours 30m
Sources:
  - feature-spec: docs/plans/engineer-density-v1.md
  - todo-md: section "Now"
maxPrs: 12
priority: todo-first
```

---

## Later (deps review / HITL) — do not implement overnight

| Item | Why deferred |
|------|----------------|
| Google Docs / Sheets export | Needs OAuth / Google API client + secrets review |
| PDF export | Needs reportlab/weasyprint (or similar) dep review |
| Frontend Vitest / RTL suite | New test runner + config leap |
| E2E Playwright import smoke | Already optional; keep gated |
| Continuous vaguely-scoped “improve algorithm forever” | Must become concrete regression fixtures / cases |
| Theme redesign for brand aesthetics only | Prefer density/speed; visual overhaul is daylight |

---

## Vertical slices (one draft PR each)

### Slice A — Custodial maturity
**id:** `feature:custodial-maturity`  
**executor:** `pr-slice`  
**risk:** low  
**acceptance:** Add MIT `LICENSE` (match heff-skills if present), root `CHANGELOG.md` (Keep a Changelog; note current alpha/MVP), mature `.gitignore` (OS junk, editor crumbs, after-hours session artifacts already present), add root `AGENTS.md` pointing at `.cursor/skills`, `.agents/skills`, `docs/development.md`, and this plan.  
**verification:** `test -f LICENSE && test -f CHANGELOG.md && test -f AGENTS.md`

### Slice B — Strict hostname URL validation (SSRF)
**id:** `feature:ssrf-url-validation`  
**executor:** `pr-slice`  
**risk:** medium  
**acceptance:** Parse hostname in `is_mcmaster_url` and `normalize_makerworld_url`; allow only McMaster / MakerWorld hosts; reject private/link-local IPs and non-http(s). Happy-path URLs stay green.  
**verification:** `pytest tests/test_guardrails.py tests/test_urls.py -q`

### Slice C — Upload size limit
**id:** `feature:upload-size-limit`  
**executor:** `pr-slice`  
**risk:** low  
**acceptance:** `POST /api/import/file` rejects oversized bodies with 413 before unbounded `file.read()`; document limit in `docs/security.md`.  
**verification:** `pytest -q -k 'import or upload'`

### Slice D — Rate-limit + cap sync-pricing
**id:** `feature:sync-pricing-limits`  
**executor:** `pr-slice`  
**risk:** medium  
**acceptance:** Rate-limit `POST /api/bom/sync-pricing`; max parts per request; re-validate McMaster URLs.  
**verification:** `pytest -q -k sync_pricing`

### Slice E — Matching preferences settings (local)
**id:** `feature:matching-preferences`  
**executor:** `feature-build`  
**risk:** medium  
**acceptance:** Add Settings page + persisted prefs (localStorage) for matching: guess mode `exact` | `lazy` (map to same_size-first vs allow wider_scope), optional “prefer length-filtered browse”, and “show wider-scope alternatives”. Wire prefs into match API client and/or backend request options without new deps. Defaults preserve today’s behavior (lazy/wider allowed).  
**verification:** `cd frontend && npm run build`

### Slice F — Exact vs lazy guess wiring
**id:** `feature:exact-lazy-guess`  
**executor:** `pr-slice`  
**risk:** medium  
**acceptance:** Backend honors `guess_mode=exact|lazy` (query or project prefs): `exact` suppresses `wider_scope` alternatives / forces length-specific filtered browse when length known; `lazy` keeps current behavior. Unit tests for bolt length cases.  
**verification:** `pytest -q -k 'guess or length or alternative'`

### Slice G — Export pack (no new deps)
**id:** `feature:export-pack`  
**executor:** `pr-slice`  
**risk:** low  
**acceptance:** Keep CSV; add TSV + XLSX export using existing `openpyxl`/`pandas`; BOM editor export menu with minimum clicks (single control, format submenu or query `?format=`). Update API docs.  
**verification:** `pytest -q -k export`

### Slice H — Multi-site ingestion scaffold
**id:** `feature:multi-site-scaffold`  
**executor:** `pr-slice`  
**risk:** low  
**acceptance:** Scaffold only — `backend/services/sites/` with `SiteAdapter` protocol, `MakerWorldAdapter` wrapping existing scrape/parse, registry stub for future Printables/Thingiverse/etc., and docs stub. No live other-site scraping.  
**verification:** `pytest -q -k site_adapter`

### Slice I — Golden BOM fixture harness + corpus seed
**id:** `feature:golden-bom-harness`  
**executor:** `feature-build`  
**risk:** medium  
**acceptance:** `tests/fixtures/golden_boms/` layout: `input.*` + `expected.json` (parts: name, qty, key specs). Pytest param harness scores parse+match against golden; ship ≥8 complex synthetic/description BOMs including OpenMANET + existing mega fixtures migrated or wrapped. Scoring report on failure.  
**verification:** `pytest tests/test_golden_boms.py -q`

### Slice J — Engineer UI density
**id:** `feature:ui-density`  
**executor:** `pr-slice`  
**risk:** medium  
**acceptance:** BomEditor: denser table (tighter row padding/typography), sticky compact toolbar (import/export/settings shortcuts), keyboard focus styles, reduce chrome without removing functions. Stay within existing Tailwind/theme tokens — no purple/glow redesign.  
**verification:** `cd frontend && npm run build`

### Slice K — Docs pass for v1 surfaces
**id:** `feature:docs-v1-pass`  
**executor:** `docs-digest`  
**outcomeKind:** `draft-pr`  
**risk:** low  
**acceptance:** Update `docs/frontend.md`, `docs/api.md`, `docs/testing.md`, `PLAN.md` Phase 10 pointers for settings/export/golden harness/multi-site scaffold; link Later deps table.  
**verification:** `test -f docs/frontend.md && rg -n 'Settings|export|golden|SiteAdapter' docs/ PLAN.md`

### Slice L — Bolt-length algorithm regressions
**id:** `feature:bolt-length-regressions`  
**executor:** `pr-slice`  
**risk:** medium  
**acceptance:** Add query-accuracy / hardware_spec cases for ambiguous lengths (“M3x10”, “M3 10mm”, glued runs) and ensure exact mode prefers length facet. Fix any clear parse miss uncovered by new cases.  
**verification:** `pytest tests/test_hardware_terms.py tests/test_description_bom.py -q`

---

## Ordering hint

todo-first / custodial → security (B,C,D) → settings+guess (E,F) → export (G) → scaffold/harness (H,I) → UI (J) → docs (K) → length algos (L).

Stop at 12 draft PRs; park remainder uncommitted on the newest relevant branch.
