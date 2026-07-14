# TODO — after-hours queue

Agent-ready overnight work for `/after-hours`. Target branch: **`dev`**.

Plan: [docs/plans/engineer-density-v1.md](docs/plans/engineer-density-v1.md)

---

## Now

- [ ] Custodial maturity (LICENSE, CHANGELOG, gitignore, AGENTS.md)
  - Acceptance: see feature-spec slice A
  - verification: `test -f LICENSE && test -f CHANGELOG.md && test -f AGENTS.md`
  - risk: low

- [ ] Strict hostname URL validation (SSRF)
  - Acceptance: see feature-spec slice B
  - verification: `pytest tests/test_guardrails.py tests/test_urls.py -q`
  - risk: medium

- [ ] Upload size limit on import file
  - Acceptance: see feature-spec slice C
  - verification: `pytest -q -k 'import or upload'`
  - risk: low

- [ ] Cap and rate-limit sync-pricing
  - Acceptance: see feature-spec slice D
  - verification: `pytest -q -k sync_pricing`
  - risk: medium

- [ ] Matching preferences settings (local)
  - Acceptance: see feature-spec slice E
  - verification: `cd frontend && npm run build`
  - risk: medium

- [ ] Exact vs lazy guess wiring
  - Acceptance: see feature-spec slice F
  - verification: `pytest -q -k 'guess or length or alternative'`
  - risk: medium

- [ ] Export pack (CSV/TSV/XLSX, no new deps)
  - Acceptance: see feature-spec slice G
  - verification: `pytest -q -k export`
  - risk: low

- [x] Multi-site ingestion scaffold (no live other sites)
  - Acceptance: see feature-spec slice H
  - verification: `pytest -q -k site_adapter`
  - risk: low

- [ ] Golden BOM fixture harness + corpus seed
  - Acceptance: see feature-spec slice I
  - verification: `pytest tests/test_golden_boms.py -q`
  - risk: medium

- [ ] Engineer UI density
  - Acceptance: see feature-spec slice J
  - verification: `cd frontend && npm run build`
  - risk: medium

- [ ] Docs pass for v1 surfaces
  - Acceptance: see feature-spec slice K
  - verification: `rg -n 'Settings|export|golden|SiteAdapter' docs/ PLAN.md`
  - risk: low

- [ ] Bolt-length algorithm regressions
  - Acceptance: see feature-spec slice L
  - verification: `pytest tests/test_hardware_terms.py tests/test_description_bom.py -q`
  - risk: medium

---

## Later (deps review)

- [ ] Google Docs / Sheets export (OAuth)
- [ ] PDF export (new packaging)
- [ ] Frontend Vitest / RTL
- [ ] Live multi-site adapters (Printables, etc.)
- [ ] Theme overhaul beyond density
- [ ] Filtered browse roots for hex_bolt / threaded_rod / set_screw
- [ ] Expand matcher beyond Fastening
- [ ] API authentication for public deploy
- [ ] Trusted-proxy X-Forwarded-For handling
- [ ] Persistent multi-user project store
