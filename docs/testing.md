# Testing

Tests live in `tests/` and use [pytest](https://docs.pytest.org/).

## Running tests

```bash
# Activate venv first
source .venv/bin/activate

# Run unit tests (skip live MakerWorld network calls) — recommended default
pytest -m 'not integration'

# Run all tests including live scrape
pytest

# Verbose output
pytest -v

# Security guardrails only
pytest tests/test_guardrails.py

# CLI regression checks (quantity + hardware validators)
pytest tests/test_regression_checks.py

# All offline validators in one script
./scripts/run_checks.sh

# Single file
pytest tests/test_parser_matcher.py
```

## Test isolation (`tests/conftest.py`)

Shared fixtures run automatically:

| Fixture | Purpose |
|---------|---------|
| `_isolated_store` | Clears in-memory BOM history before/after each test |
| `_reset_rate_limits` | Resets per-IP and outbound rate limiter state |
| `api_client` | `httpx.AsyncClient` against the FastAPI app (optional) |

Integration tests use `@pytest.mark.integration` and are excluded by default.

## Guardrails (`tests/test_guardrails.py`)

Security and hygiene checks that **fail the build** when violated:

| Test | What it catches |
|------|-----------------|
| `test_api_responses_do_not_leak_credentials` | McMaster API username/password/cert path in JSON responses |
| `test_import_file_response_*` / `test_bom_get_*` | Same leak-bait scan on import and BOM endpoints |
| `test_health_never_exposes_credential_config` | Health payload must not mention McMaster credentials |
| `test_global_exception_handler_hides_traceback_when_debug_off` | 500 responses omit traceback when `DEBUG=0` |
| `test_feedback_response_does_not_leak_credentials` | Feedback dispatch config (GitHub token, SMTP password) not in JSON |
| `test_debug_proxy_env_redacts_credentials` | `/api/debug` redacts `user:pass@` in proxy URLs |
| `test_tracked_files_do_not_include_env` | `.env` / `.env.*` must not be git-tracked |
| `test_tracked_source_has_no_obvious_secrets` | Private keys, cloud tokens, hardcoded credentials in committed files |

Leak-bait values live in `tests/guardrails.py` and are injected via `monkeypatch` — they must never appear in API output.

Known gaps (SSRF URL validation, `sync-pricing` limits, upload size) are tracked in [Security](security.md). Several have draft after-hours PRs against `dev`.

## Golden BOM corpus (`tests/test_golden_boms.py`)

Complex MakerWorld-style description BOMs live under `tests/fixtures/golden_boms/<case>/`:

| File | Role |
|------|------|
| `input.txt` | Raw prose / run-on BOM text |
| `expected.json` | Locked name + quantity truth |

Score must be **100%** name+qty match. Expand this corpus when adding parser diversity; regenerate expected only with intentional parser changes.

```bash
pytest tests/test_golden_boms.py -q
```

## Multi-site scaffold

`backend/services/sites/` (`SiteAdapter` + `MakerWorldAdapter` registry) is scaffold-only — no live Printables/Thingiverse ingestion until daylight review. See `docs/backend/sites.md` when that PR merges.

## Regression CLI checks (`tests/test_regression_checks.py`)

Wraps the runtime validator scripts so golden fixtures stay clean:

| Test | Script |
|------|--------|
| `test_check_bom_quantities_script_passes_mega_python_fixture` | `scripts/check_bom_quantities.py` |
| `test_check_hardware_specs_script_passes_matched_mega_python` | `scripts/check_hardware_specs.py --match` |
| `test_check_bom_specifications_script_passes_sample_bom` | `scripts/check_bom_specifications.py` on `data/sample_bom.csv` |
| `test_check_catalog_integrity_script_passes` | `scripts/check_catalog_integrity.py` |

`tests/test_catalog_integrity.py` also imports `check_catalog_integrity()` directly.

Run everything offline:

```bash
./scripts/run_checks.sh
```

These assert **exit code 0** on `tests/fixtures/description_mega_python.txt` (quantity/hardware) and `data/sample_bom.csv` (specifications). Also runs:

- `scripts/mcmaster_cross_test.py` — offline McMaster matcher ↔ pipeline parity
- `tests/test_query_accuracy.py` — dummy BOM listing query-accuracy fixture
- `tests/test_notebook_pipeline_parity.py` — notebook ↔ website pipeline drift checks
- `tests/test_feedback.py` + `tests/test_feedback_dispatch.py` — report form + outbound channels (mocked HTTP)

## McMaster cross-test

Curated cases: `data/mcmaster_regression_urls.json`  
Query-accuracy cases: `tests/fixtures/bom_listing_query_cases.json`

| Command | Network | What it compares |
|---------|---------|------------------|
| `python scripts/mcmaster_cross_test.py` | No | `match_part` vs `match_parts_only` vs expectations |
| `pytest tests/test_query_accuracy.py` | No | Per-line URL/finish expectations from dummy BOM listing |
| `python scripts/mcmaster_cross_test.py --live` | Yes | Above + live browse fetch |

Tests: `tests/test_mcmaster_cross_test.py` (offline always; one `@integration` live case).

## CI

GitHub Actions:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `.github/workflows/test.yml` | Push / PR to `main` | `pytest -m 'not integration'`, regression CLI, guardrails |
| `.github/workflows/monthly-taxonomy-crawl.yml` | 1st of month + manual | McMaster taxonomy crawl → PR when data changes |

Local equivalent: `./scripts/run_checks.sh` (offline validators) and `./scripts/run_monthly_taxonomy_crawl.sh` (live crawl).

## Test files

### `tests/test_parser_matcher.py`

Unit tests for the parser and matcher services.

| Test | What it verifies |
|------|------------------|
| `test_parse_bom_csv` | `parse_bom_bytes` reads CSV with `Qty` and `Part Name` columns |
| `test_matcher_generates_url` | `match_part` produces a URL containing `mcmaster.com` |
| `test_score_confidence_with_hardware_keyword` | Hardware keywords score ≥ 0.5 |

Sample data: `data/sample_bom.csv`.

---

### `tests/test_api.py`

FastAPI route tests using `httpx.AsyncClient` + `ASGITransport` (no live server).

| Test | What it verifies |
|------|------------------|
| `test_health` | `GET /api/health` returns `status: ok` |
| `test_list_import_stages` | Seven stages; `enrich_mcmaster` maps to `05_api_payload.ipynb` |
| `test_import_bom_file` | File upload import returns project + parts |
| `test_list_notebooks` | `GET /api/notebooks` returns notebooks array |
| `test_import_sources` | MakerWorld examples and upload format metadata |

---

### `tests/test_feedback.py` / `tests/test_feedback_dispatch.py`

Match-error report form (`POST /api/feedback/match-error`).

| Area | Tests |
|------|-------|
| Persistence | JSONL append, project enrichment, MakerWorld vs McMaster sides |
| Dispatch | Email/GitHub/webhook formatters; `pytest-httpx` mocks for outbound HTTP |
| Guardrails | Feedback credentials never appear in API JSON (`test_guardrails.py`) |

See [Feedback dispatch](backend/feedback-dispatch.md).

---

### `tests/test_query_accuracy.py`

Offline McMaster query accuracy from `tests/fixtures/bom_listing_query_cases.json` — URL fragments, finish counts, `selected_finish_id` per hardware line (no app or network).

---

### `tests/test_category_coverage.py`

McMaster category and taxonomy alignment (mostly offline).

| Test | What it verifies |
|------|------------------|
| `test_twenty_six_top_level_metacategories` | `mcmaster_metacategories.json` matches site nav |
| `test_all_matcher_categories_have_metacategory` | Every matcher category maps to a department |
| `test_crawled_fastening_families_map_to_fastening_department` | Monthly crawl slugs → `fastening_and_joining` |
| `test_matcher_category_routes_resolve_http` | Live HTTP 200 for all matcher routes (`@integration`) |

Refresh crawl data: `./scripts/run_monthly_taxonomy_crawl.sh`. See [McMaster taxonomy](backend/mcmaster-taxonomy.md).

---

### `tests/test_notebook_pipeline_parity.py`

Ensures numbered notebooks (`01`–`05`) call `backend.services.pipeline`, avoid bypass patterns (`parse_bom_bytes`, direct `matcher.match_parts`), and match `import_from_file` / `parts_from_scrape_result` branching.

---

### `tests/test_searchability.py`

Non-searchable BOM lines (instructions, markup, placeholders) → `not_applicable`; no Standard Components fallback URLs.

---

### `tests/test_nut_washer_matching.py` / `tests/test_head_type_matching.py` / `tests/test_finish_browse.py`

Metric nut/washer browse roots, screw head-type routing, single-default finish browse tables.

---

### `tests/test_browse_finish_hydrate.py` / `tests/test_hydration_dedup.py` / `tests/test_browse_web_first.py`

Live browse hydration policies (`lowest_price`, finish selection), session dedupe, web-first ranking.

---

### `tests/test_pricing.py` / `tests/test_pricing_listing.py`

McMaster listing price sync and BOM pricing API.

---

### `tests/test_makerworld_bom.py`

BOM extraction from captured MakerWorld `__NEXT_DATA__` fixtures.

| Test | What it verifies |
|------|------------------|
| `test_parts_from_kumiko_fixture` | Kumiko design: Maker's Supply, filaments, other parts |
| `test_parts_from_magnet_fixture` | Magnet kit quantities |
| `test_extract_next_data_from_html` | `__NEXT_DATA__` script tag parsing |
| `test_score_attachment` / `test_best_attachment` | CSV/XLSX link ranking |
| `test_live_makerworld_description_bom` | Live Mega Python URL — description BOM (`@pytest.mark.integration`) |

Fixtures in `tests/fixtures/`. Regression URLs in `data/regression_urls.json`.

---

### `tests/test_description_bom.py` / `tests/test_quantity_checks.py`

Description BOM parsing and quantity field placement (`parsers/makerworld/description.py`, `parsers/helpers/quantity_checks.py`).

---

### `tests/test_hardware_match_verify.py`

Metric size/length extraction and post-match catalog verification (`hardware_spec.py`, `hardware_match_verify.py`).

---

### CLI regression scripts

| Script | Purpose |
|--------|---------|
| `scripts/parse_description_bom.py` | Dump description BOM as JSON |
| `scripts/check_bom_quantities.py` | Validate qty not stuck in `specification` |
| `scripts/check_bom_specifications.py` | Validate `specification` holds metadata only |
| `scripts/check_hardware_specs.py` | Validate metric size/length vs catalog match |
| `scripts/check_catalog_integrity.py` | Catalog keys/titles vs `M3_SOCKET_HEAD_BY_LENGTH_MM` |
| `scripts/run_checks.sh` | Run all offline validators on golden fixtures |
| `scripts/run_monthly_taxonomy_crawl.sh` | Monthly McMaster taxonomy crawl + offline coverage tests |
| `scripts/crawl_mcmaster_taxonomy.py` | Low-level ProdPageWebPart taxonomy extractor |

---

### `tests/test_match_confidence.py`

Tier-aware `mcmaster_status` / `match_tier` for search-only rows (`resolve_match_status`).

### `tests/test_spreadsheet_regression.py`

Captured MakerWorld-style CSV/XLSX export fixtures (`tests/fixtures/makerworld_export_bom.csv`) — parse, match, and `import_from_file` pipeline.

### `tests/test_mcmaster_vendor.py`

McMaster vendor adapter: filter slugs, tier resolution, browse JSON fixture, API payload parsing.

### `tests/test_mcmaster_catalog.py` / `tests/test_mcmaster_handler.py`

Catalog part-number lookup and McMaster category-scoped search URLs.

### `tests/test_catalog_integrity.py`

Offline checks that catalog JSON keys, titles, and `M3_SOCKET_HEAD_BY_LENGTH_MM` agree.

---

### `tests/test_rate_limit.py`

| Test | What it verifies |
|------|------------------|
| `test_import_rate_limit_blocks_excess` | Per-IP limit raises 429 with `Retry-After` |
| `test_import_rate_limit_disabled` | `RATE_LIMIT_ENABLED=0` allows unlimited imports |
| `test_outbound_min_interval` | `outbound_request()` enforces min spacing |
| `test_health_reports_rate_limit_config` | Health endpoint exposes rate-limit settings |

---

### `tests/test_debug.py`

Debug mode logging and `/api/debug` endpoints.

---

### `tests/test_http_client.py`

HTTP client helpers: browser headers, proxy error unwrapping, error formatting.

---

### `tests/test_notebook_utils.py`

Jupyter helpers: `prepare_crawl_env`, offline fallbacks, regression URL picker, `parse_bom_only` + `match_parts_only` parity with API stages.

---

### `tests/test_notebook_frames.py`

Structured DataFrame helpers for notebook display (`parts_to_dataframe`, browse rows).

---

### `tests/test_scraper_thumbnail.py`

Thumbnail URL extraction from scraped HTML.

---

## Adding tests

### Parser changes

Add cases to `test_parser_matcher.py` with inline CSV bytes or files from `data/`:

```python
def test_parse_custom_columns():
    csv = b"Amount,Component,Details\n2,Widget,Large\n"
    parts = parse_bom_bytes(csv, "bom.csv")
    assert parts[0].original_name == "Widget"
```

### Matcher changes

Test query generation and confidence independently:

```python
def test_normalize_removes_3d_print():
    from backend.services.matcher import normalize_hardware_name
    assert "printed" not in normalize_hardware_name("3D printed spacer", "")
```

### API changes

Add async route tests in `test_api.py`:

```python
@pytest.mark.asyncio
async def test_import_invalid_url():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/import", json={"url": "https://example.com"})
    assert response.status_code == 400
```

### Rate limit tests

Use `reset_rate_limits_for_tests()` (auto-applied via `conftest.py`) or set `RATE_LIMIT_ENABLED=0` in fixtures when testing import flows.

### Guardrail / regression tests

After parser or matcher changes, run:

```bash
pytest tests/test_guardrails.py tests/test_regression_checks.py
./scripts/check_bom_quantities.py tests/fixtures/description_mega_python.txt
```

## What is not tested yet

- Frontend component tests (Vitest/RTL)
- End-to-end browser import with real URLs (use notebooks + `@integration` tests)
- Live SMTP email send (dispatch email channel is config-gated; not exercised in CI)
- Live GitHub issue creation (mocked via `pytest-httpx` in CI)

See [PLAN.md](../PLAN.md) Phase 10 for the active backlog.
