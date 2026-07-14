# TODO — after-hours queue

Agent-ready overnight work for `/after-hours`. Keep **Now** thin (≤ `maxPrs`) and acceptance testable. Vague / product-decision items stay in **Later**.

Target branch for draft PRs: **`dev`** (semi-stable **`main`** stays merge-only / daylight).

---

## Now

AFK-safe Phase 10 security slices. Each item is one draft PR.

- [ ] Strict hostname URL validation (SSRF)
  - Files: `backend/services/vendors/mcmaster/urls.py` (`is_mcmaster_url`), `backend/services/scraper.py` (`normalize_makerworld_url`)
  - Acceptance: parse hostname; allow only `*.mcmaster.com` / `*.makerworld.com` (and www variants as needed); reject private/link-local IPs and non-http(s) schemes; keep existing happy-path URLs green
  - verification: `pytest tests/test_guardrails.py tests/test_urls.py -q` (add `tests/test_urls.py` if missing)
  - risk: medium

- [ ] Cap and rate-limit `POST /api/bom/sync-pricing`
  - Files: `backend/routers/bom_router.py`, `backend/rate_limit.py`
  - Acceptance: rate limit + max parts per request; re-validate every `mcmaster_url` with the strict hostname helper from the SSRF slice (or temporary shared allowlist if that PR is not yet merged — document dependency in PR body)
  - verification: `pytest -q -k sync_pricing`
  - risk: medium

- [ ] Upload size limit on `POST /api/import/file`
  - Files: `backend/routers/import_router.py`
  - Acceptance: reject oversized uploads with HTTP 413 before full `file.read()`; document limit in `docs/security.md`
  - verification: `pytest -q -k import`
  - risk: low

---

## Later

Daylight / larger / HITL — do not pull into overnight Sources until sliced with Agent Briefs.

### Matching

- [ ] Filtered browse roots for `hex_bolt`, `threaded_rod`, `set_screw`
- [ ] Expand matcher categories beyond Fastening (Power Transmission, Sealing, pipe fittings)
- [ ] Cross-check `hardware_spec.py` vs McMaster API `Specifications[]`
- [ ] Promote high-value taxonomy families into `mcmaster_categories.json`

### Frontend & E2E

- [ ] Frontend component tests (Vitest / RTL)
- [ ] E2E browser import smoke (`@integration` gated)

### Ops & security (needs product choices)

- [ ] Trusted-proxy handling for `X-Forwarded-For` rate-limit keys
- [ ] `http(s)`-only external links in BOM editor (+ optional API validation)
- [ ] API authentication before any public deployment
- [ ] Persistent project store if multi-user needed
- [ ] Live SMTP / GitHub dispatch smoke tests

### Docs

- [ ] Notebook refresh when Phase 10 matcher categories land
