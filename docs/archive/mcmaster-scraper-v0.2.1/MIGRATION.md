# McMaster-scraper archive (v0.2.1)

Upstream [thedjchi/mcmaster-scraper](https://github.com/thedjchi/mcmaster-scraper) was vendored in-tree for parity testing and then **migrated into our codebase** (July 2026).

| Field | Value |
|-------|-------|
| Upstream version | `0.2.1` (see `VERSION`) |
| Upstream commit | See `UPSTREAM_COMMIT` |
| License | MIT (`LICENSE`) |

## What we kept (in-house)

| Archived upstream | Migrated to |
|-------------------|-------------|
| `_api/scraper.py` — Playwright ProdPageWebPart discovery | `backend/services/vendors/mcmaster/browse_scrape.py` |
| `_utils/page_provider.py` — Chromium + stealth session | Same module (`browse_scrape.py`) |
| `_api/table_parser.py` + `_text_parser.py` | Already in `backend/services/vendors/mcmaster/browse_parse.py` |
| `sync_api.py` / `async_api.py` | Removed — `browse_fetch.py` calls scrape + parse directly |
| `_utils/cache.py` | Not migrated (no disk cache yet; add if needed) |

## When browse fetch fails

1. Compare live JSON shape to `tests/fixtures/mcmaster_product_presentations_min.json`
2. Re-read upstream `mcmaster_scraper/_api/scraper.py` in this archive
3. Check `docs/archive/mcmaster-scraper-v0.2.1/ANALYSIS.md` for the old integration map
4. Run offline checks: `python scripts/mcmaster_browse_example.py --offline`
5. Run cross-test: `python scripts/mcmaster_cross_test.py`

## Runnable demos (current repo)

```bash
python scripts/mcmaster_browse_example.py --offline
MCMASTER_BROWSE_RESOLVE_ENABLED=1 python scripts/mcmaster_browse_example.py
python scripts/mcmaster_cross_test.py
pytest tests/test_mcmaster_browse.py tests/test_mcmaster_cross_test.py -m 'not integration'
```

Notebook: `notebooks/mcmaster_browse.ipynb`
