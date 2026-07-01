# McMaster vendor scraper — test plan

Per-component checklist for the vendored package (`vendor/mcmaster_scraper/mcmaster_scraper/`) and repo integration (`backend/services/vendors/mcmaster/`). Use with [ANALYSIS.md](./ANALYSIS.md) for architecture context.

**Default CI:** offline tests only (`pytest -m 'not integration'`).

**Live tests:** require `pip install -e '.[playwright]'`, `playwright install chromium`, and `MCMASTER_BROWSE_RESOLVE_ENABLED=1`.

---

## How to run

```bash
# Offline (recommended for CI)
pytest tests/test_mcmaster_scraper_vendored.py \
       tests/test_mcmaster_vendor.py \
       tests/test_mcmaster_cross_test.py \
       -m 'not integration' -q

# Live browse (manual / nightly)
MCMASTER_BROWSE_RESOLVE_ENABLED=1 \
pytest tests/test_mcmaster_scraper_vendored.py \
       tests/test_mcmaster_cross_test.py \
       -m integration -q

# Fixture-only scraper demo (no pytest)
python scripts/mcmaster_scraper_example.py --offline
```

---

## Vendored package — per-module checklists

### `__init__.py`

| # | Test case | Type | Status |
|---|-----------|------|--------|
| 1 | Package imports without side effects | unit | ✅ `test_mcmaster_scraper_package_is_vendored` |
| 2 | `__file__` resolves under `vendor/mcmaster_scraper/` | unit | ✅ same |

---

### `sync_api.py`

| # | Test case | Type | Status |
|---|-----------|------|--------|
| 1 | `get_products_from_url` returns DataFrame with `Part Number` column (mocked scraper) | unit | ❌ |
| 2 | Invalid URL propagates `ValueError` | unit | ❌ |
| 3 | Page without `ProductPresentations` propagates `UnsupportedOperation` | unit | ❌ |
| 4 | `get_products_from_urls` returns list aligned with input order | unit | ❌ |
| 5 | End-to-end on fixture-backed mock (no Playwright) | unit | ❌ |
| 6 | Live URL returns non-empty table | integration | 🔒 manual / example script |

---

### `async_api.py`

| # | Test case | Type | Status |
|---|-----------|------|--------|
| 1 | Cache hit skips `get_product_api_response` (mock) | unit | ✅ `test_vendored_cache_set_and_get_roundtrip` |
| 2 | `refresh=True` bypasses cache | unit | ❌ |
| 3 | `get_products_from_urls` runs concurrently (mock timing) | unit | ❌ |
| 4 | Output columns match sync_api for same payload | unit | ❌ |
| 5 | Live fetch via bridge | integration | 🔒 `run_live_case` |

---

### `_api/scraper.py`

| # | Test case | Type | Status |
|---|-----------|------|--------|
| 1 | `_is_valid_url` accepts `https://www.mcmaster.com/...` | unit | ❌ |
| 2 | `_is_valid_url` accepts `https://mcmaster.com/...` | unit | ❌ |
| 3 | `_is_valid_url` rejects non-McMaster hosts | unit | ❌ |
| 4 | `_extract_json_from_response` parses leading/trailing whitespace | unit | ❌ |
| 5 | `_extract_json_from_response` raises when no `{`/`}` | unit | ❌ |
| 6 | `_extract_json_from_response` handles nested braces (rfind end) | unit | ❌ |
| 7 | `get_product_api_response` discovers ProdPageWebPart URL | integration | 🔒 |
| 8 | Invalid product URL fails gracefully | integration | 🔒 |

---

### `_api/table_parser.py`

| # | Test case | Type | Status |
|---|-----------|------|--------|
| 1 | Minimal fixture → one row, `Part Number` == `91290A120` | fixture | ✅ `test_vendored_table_parser_matches_fixture` |
| 2 | `Length` column parsed | fixture | ✅ `test_dataframe_to_browse_rows_from_vendored_parser` |
| 3 | Missing `ProductPresentations` → `UnsupportedOperation` | unit | ❌ |
| 4 | Multiple product types → `Product Type` column added | fixture | ❌ |
| 5 | Multiple subtypes → `Product Subtype` column added | fixture | ❌ |
| 6 | Empty `PrimaryProductGroup.ColumnIds` falls back to all columns | fixture | ❌ |
| 7 | Horizontal pivot grouping rows (multi-part rows) | fixture | ❌ |
| 8 | Parity with in-house `parse_product_presentations` | fixture | ✅ `test_vendored_and_inhouse_parsers_agree_on_fixture` |

---

### `_api/_text_parser.py`

| # | Test case | Type | Status |
|---|-----------|------|--------|
| 1 | `PART_NUMBER` type → `"Part Number"` header | unit | ❌ (indirect ✅ via fixture) |
| 2 | `PRICING` type → `"Price"` header | unit | ❌ |
| 3 | Plain numeric cell → `float` | unit | ❌ |
| 4 | Fraction text (`1 1/2`) → `float` | unit | ❌ |
| 5 | Non-numeric text preserved as `str` | unit | ❌ |
| 6 | Empty text → `""` | unit | ❌ |

---

### `_utils/cache.py`

| # | Test case | Type | Status |
|---|-----------|------|--------|
| 1 | `set_cached(url, data)` then `get_cached(url)` returns same dict | unit | ❌ **fails today — key mismatch** |
| 2 | Different URLs → different cache entries | unit | ❌ |
| 3 | Cache directory created under platformdirs | unit | ❌ |
| 4 | LRU eviction under size pressure | unit | ❌ |
| 5 | `refresh=True` at API layer ignores stale entry | unit | ❌ |

**Expected failure until bug fixed:** test #1 documents that `get_cached` uses `md5(url)` while `set_cached` stores under raw URL.

---

### `_utils/page_provider.py`

| # | Test case | Type | Status |
|---|-----------|------|--------|
| 1 | `get_page()` returns usable Playwright page | integration | 🔒 implicit in live fetch |
| 2 | Concurrent `get_page()` calls do not corrupt context | integration | ❌ |
| 3 | Stealth wrapper applied (navigator check optional) | integration | ❌ |
| 4 | Page closed after scraper completes | integration | 🔒 code review |

---

### `_utils/event_loop_wrapper.py`

| # | Test case | Type | Status |
|---|-----------|------|--------|
| 1 | `run_in_loop_sync` returns coroutine result from sync context | unit | ❌ |
| 2 | `run_in_loop_async` callable from running asyncio loop | unit | ❌ |
| 3 | Nested calls do not deadlock | unit | ❌ |
| 4 | Cancellation propagates (`CancelledError`) | unit | ❌ |
| 5 | Implicit coverage via sync_api in live example | integration | 🔒 |

---

## Repo integration — per-module checklists

### `scraper_bridge.py`

| # | Test case | Type | Status |
|---|-----------|------|--------|
| 1 | `get_products_table_from_json` on min fixture | fixture | ✅ |
| 2 | `_normalize_product_presentations` converts string keys to int | unit | ❌ (behavior covered indirectly) |
| 3 | `_normalize_product_presentations` passes through non-PP root unchanged | unit | ❌ |
| 4 | `_require_scraper` message when package missing | unit | ❌ |
| 5 | `aget_browse_rows` matches `dataframe_to_browse_rows(get_products_table(...))` | unit | ❌ |
| 6 | Live `aget_products_dataframe` | integration | 🔒 cross_test |

---

### `browse_fetch.py`

| # | Test case | Type | Status |
|---|-----------|------|--------|
| 1 | Raises when `MCMASTER_BROWSE_RESOLVE_ENABLED` not set | unit | ✅ `test_live_browse_fetch_disabled_by_default` |
| 2 | Raises on non-McMaster URL | unit | ❌ |
| 3 | `resolve_part_from_browse` picks row by hint | unit | ❌ |
| 4 | `resolve_part_from_browse` returns sole row when one row | unit | ❌ |
| 5 | `resolve_part_from_browse` returns None when ambiguous | unit | ❌ |
| 6 | Live fetch returns rows for filtered browse URL | integration | 🔒 `test_live_cross_test_filtered_browse` |

---

### `browse_parse.py`

| # | Test case | Type | Status |
|---|-----------|------|--------|
| 1 | `parse_product_presentations` on min fixture | fixture | ✅ `test_parse_product_presentations_fixture` |
| 2 | `dataframe_to_browse_rows` skips NaN / empty part numbers | unit | ❌ |
| 3 | `find_row_by_part_number` case-insensitive | unit | ❌ |
| 4 | Product type/subtype preserved from DataFrame columns | fixture | ⚠️ partial in vendored test |

---

### `enrichment.py`

| # | Test case | Type | Status |
|---|-----------|------|--------|
| 1 | Skips when browse disabled | unit | ❌ |
| 2 | Skips when part already has `mcmaster_part_number` | unit | ❌ |
| 3 | Skips when tier != `filtered_browse` | unit | ❌ |
| 4 | Successful resolve updates part number + URL + confidence | unit | ❌ |
| 5 | Browse failure leaves part unchanged | unit | ❌ |
| 6 | `enrich_part_with_api` when API configured (mock httpx) | unit | ❌ (API tested separately) |

---

### `cross_test.py`

| # | Test case | Type | Status |
|---|-----------|------|--------|
| 1 | Regression catalog loads (≥5 cases) | unit | ✅ `test_mcmaster_regression_catalog_loads` |
| 2 | All offline cases pass | unit | ✅ `test_offline_cross_test_all_pass` |
| 3 | `match_part` == `match_parts_only` on catalog case | unit | ✅ |
| 4 | Live case: bridge vs scraper part sets match | integration | 🔒 |
| 5 | Live case: expected SKUs present in table | integration | 🔒 |
| 6 | Report formatter includes pass/fail counts | unit | ❌ |

---

## Cross-cutting scenarios

### Parser parity (offline)

| # | Scenario | Status |
|---|----------|--------|
| 1 | Min fixture: vendored DataFrame vs in-house `BrowseRow` part numbers | ✅ |
| 2 | Additional fixtures for multi-table pages | ❌ |
| 3 | Saved live JSON snapshots in `tests/fixtures/` | ❌ |

### Matcher → browse URL → table (live)

| # | Scenario | Status |
|---|----------|--------|
| 1 | M3×16 SHCS black oxide — table contains expected catalog SKU | 🔒 |
| 2 | Browse URL from matcher matches cross-test `browse_url` override | 🔒 |
| 3 | Row count > 0 for standard fastener filters | 🔒 |

### Regression catalog

| # | Scenario | Status |
|---|----------|--------|
| 1 | Every case: `match_tier` and URL fragments | ✅ offline |
| 2 | Cases with `offline_fixture`: parser parity | ✅ offline |
| 3 | Cases with `live.expect_part_numbers_contain` | 🔒 |

---

## Recommended new tests (priority order)

1. **`test_cache_round_trip`** — `cache.py`; assert get after set; expect failure until md5 fix.
2. **`test_normalize_product_presentations_string_keys`** — explicit unit test in bridge.
3. **`test_is_valid_url_matrix`** — parametrized scraper URL validation.
4. **`test_extract_json_from_response`** — pure function, no Playwright.
5. **`test_resolve_part_from_browse_*`** — mock `fetch_browse_rows`.
6. **`test_multi_table_fixture`** — extend golden fixtures when live snapshots captured.
7. **`test_sync_async_fixture_parity`** — inject mock `get_product_api_response`.

---

## Test data

| Asset | Purpose |
|-------|---------|
| `tests/fixtures/mcmaster_product_presentations_min.json` | Single-row socket head screw table |
| `data/mcmaster_regression_urls.json` | Cross-test case catalog (matcher + live hints) |
| `data/mcmaster_catalog.json` | Offline SKU lookup (upstream of browse URLs) |
| `data/mcmaster_browse_roots.json` | Finish-specific browse roots for filtered URLs |

---

## Sign-off checklist (release / upstream merge)

- [ ] Offline pytest green: `pytest -m 'not integration'`
- [ ] Parser parity on all fixtures with `offline_fixture` in regression catalog
- [ ] Cache round-trip test passes (or bug documented and tracked)
- [ ] `VERSION` / `UPSTREAM_COMMIT` updated after vendor sync
- [ ] Live smoke: one `filtered_browse` case with browse enabled (optional)
- [ ] No Playwright/browser tests added to default CI job
- [ ] ANALYSIS.md Known bugs section updated if upstream fixes cache
