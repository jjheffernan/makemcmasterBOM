# McMaster taxonomy crawl and category data

McMaster's public browse UI exposes product-family tiles through the same
`ProdPageWebPart.aspx` JSON the website uses for filtered tables. We crawl that
structure **offline from routing config** and refresh it **monthly** so category
mappings stay current without hammering the site on every import.

## Monthly batch job

| Item | Detail |
|------|--------|
| **Schedule** | 1st of each month, 12:00 UTC |
| **Workflow** | [.github/workflows/monthly-taxonomy-crawl.yml](../../.github/workflows/monthly-taxonomy-crawl.yml) |
| **Local script** | `./scripts/run_monthly_taxonomy_crawl.sh` |
| **Crawl script** | `scripts/crawl_mcmaster_taxonomy.py --batch` |
| **Scope** | 19 Fastening & Joining child browse pages (screws, nuts, washers, …) |
| **Politeness** | 5–6 s delay between page fetches (`MCMASTER_CRAWL_DELAY_SECONDS`) |
| **Output PR** | Opens a PR when `data/mcmaster_site_taxonomy.json` or metacategory slugs change |

Top-level department landing pages are **skipped in batch mode** — they often
time out on `ProdPageWebPart` and are already validated via lightweight HTTP
checks in `tests/test_category_coverage.py`.

### Run locally

```bash
pip install -e ".[playwright]"
playwright install chromium

# Polite monthly defaults (fastening child pages only)
./scripts/run_monthly_taxonomy_crawl.sh

# Also merge fastening slugs into mcmaster_metacategories.json
./scripts/run_monthly_taxonomy_crawl.sh --sync-metacategories

# Ad-hoc full crawl (interactive — not for CI)
python scripts/crawl_mcmaster_taxonomy.py --delay 5
```

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MCMASTER_CRAWL_DELAY_SECONDS` | `5` | Pause between Playwright page loads |
| `MCMASTER_CRAWL_MAX_ERRORS` | `3` | Batch exit code 1 when exceeded |

### Cron (without GitHub Actions)

```cron
0 12 1 * * cd /path/to/makemcmasterBOM && ./scripts/run_monthly_taxonomy_crawl.sh --sync-metacategories
```

Review the git diff and commit manually after a local run.

## Data files

All paths under `data/`. See also [data/README.md](../../data/README.md).

### `mcmaster_site_taxonomy.json` (crawl output)

**Written by:** `scripts/crawl_mcmaster_taxonomy.py`

| Field | Meaning |
|-------|---------|
| `crawled_at` | ISO-8601 UTC timestamp of the crawl |
| `crawl_mode` | `fastening_children` (batch) or `full` |
| `delay_seconds` | Delay used between fetches |
| `fastening_children` | Per-page `{ slug, url, groups[] }` from ProdPageWebPart |
| `groups[].department` | McMaster department header above a tile row (e.g. `Fastening and Joining`) |
| `groups[].tiles[]` | `{ title, slug, href, product_count }` product-family links |
| `summary` | Counts: child pages, fastening families, errors |
| `errors` | Pages that failed (slug + error message) |

Tile slugs often include McMaster suffixes (`socket-head-screws-2~`). Normalize
with `normalize_product_slug()` in `metacategories.py` before lookup.

**Consumers:** `tests/test_category_coverage.py` (offline validation), human
review when expanding `mcmaster_categories.json`.

### `mcmaster_metacategories.json` (department routing)

**Maintained by:** hand-edited + optional `--sync-metacategories` after crawl

| Section | Purpose |
|---------|---------|
| `metacategories[]` | 26 top-level McMaster nav departments (`id`, `label`, `route`, `slug`) |
| `category_metacategory` | Matcher category id → department id (e.g. `hex_nut` → `fastening_and_joining`) |
| `product_slugs` | `/products/{slug}/` segment → department id; crawl sync adds fastening families |
| `bom_intent_signals` | Keywords for inferring BOM department from line text |
| `coverage_audit` | Counts + `last_taxonomy_crawl` after sync |

**Code:** `backend/services/vendors/mcmaster/metacategories.py`

### `mcmaster_categories.json` (matcher browse routes)

**Maintained by:** hand-edited when adding BOM-relevant families

Each `categories[]` entry:

| Field | Purpose |
|-------|---------|
| `id` | Internal matcher id (`socket_head_screw`, `hex_bolt`, …) |
| `route` | McMaster browse root (`/products/set-screws/`) |
| `signals` | Keywords that route BOM lines to this category |
| `priority` | Tie-break when multiple categories match |
| `catalog_categories` | Optional link to generic catalog families |

`excluded_routes` documents routes we never use (Standard Components).

### `mcmaster_category_routing.json` (escape / parent routing)

**Maintained by:** hand-edited alongside new categories

| Field | Purpose |
|-------|---------|
| `parent_id` | Broad parent (`screw` → `socket_head_screw`) |
| `catalog_size` | Approximate SKU count for tie-breaking |
| `escape_keywords` | Narrow a broad parent when these phrases appear |

**Code:** `backend/services/vendors/mcmaster/category_router.py`

### `mcmaster_browse_roots.json` (filtered browse finishes)

Material/finish sub-paths **before** facet segments (`thread-size~m3/`, etc.).

**Code:** `backend/services/vendors/mcmaster/browse_roots.py`

### `mcmaster_catalog.json` (SKU fallback)

Phrase → part number when live browse resolve is off. Not updated by taxonomy crawl.

### `mcmaster_regression_urls.json`

Offline matcher regression fixtures. Not updated by taxonomy crawl.

## How crawl results become matcher changes

The monthly job **does not** auto-add matcher categories. Typical workflow:

1. Monthly PR refreshes `mcmaster_site_taxonomy.json` (+ `product_slugs` sync).
2. Review `summary.errors` and new fastening family slugs.
3. For high-value BOM families, add entries to:
   - `mcmaster_categories.json` (route + signals)
   - `mcmaster_category_routing.json` (escape keywords)
   - `mcmaster_browse_roots.json` (finish tables, when filtered browse applies)
4. Run `pytest tests/test_category_coverage.py` and `tests/test_query_accuracy.py`.

## Tests

```bash
# Offline — always in CI
pytest tests/test_category_coverage.py -m "not integration" -q

# Live route smoke (optional)
pytest tests/test_category_coverage.py -m integration -q
```

| Test | Validates |
|------|-----------|
| `test_twenty_six_top_level_metacategories` | Nav alignment in `mcmaster_metacategories.json` |
| `test_all_matcher_categories_have_metacategory` | Every matcher category mapped to a department |
| `test_crawled_fastening_families_map_to_fastening_department` | Crawl slugs resolve to `fastening_and_joining` |
| `test_matcher_category_routes_resolve_http` | All matcher routes return HTTP 200 (integration) |

## Relationship to live browse resolve

| Concern | Taxonomy crawl | Import-time browse resolve |
|---------|----------------|----------------------------|
| **When** | Monthly batch | Per BOM line on import (optional) |
| **Playwright** | Yes — one page at a time with delay | Yes — one filtered URL per line |
| **Purpose** | Validate routes / discover families | Pick a part number from a live table |
| **Default in CI** | Monthly workflow only | Disabled (`MCMASTER_BROWSE_RESOLVE_ENABLED=0`) |

Keep import-time browse off in CI and notebooks unless you explicitly need live SKUs.
See [McMaster vendor adapter](mcmaster.md#browse-table-resolution-optional-live).

## Module map

```
scripts/crawl_mcmaster_taxonomy.py   # ProdPageWebPart tile extraction
scripts/run_monthly_taxonomy_crawl.sh
backend/services/vendors/mcmaster/
├── metacategories.py                # department + slug lookup
├── category_router.py               # keyword → category
└── browse_scrape.py                 # Playwright JSON fetch (shared)
```
