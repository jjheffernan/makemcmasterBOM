# McMaster-Carr vendor adapter

McMaster linking uses **six offline tiers** plus two **optional live** enrichment paths. This document is the reference implementation for other supplier adapters — see [Vendor adapters](vendors.md).

## Tier order (offline)

| Tier | `match_tier` | When | Confidence hint |
|------|--------------|------|-----------------|
| 1 | `catalog` | Phrase hit in `data/mcmaster_catalog.json` | 1.0 |
| 2 | `rule` | `mcmaster_catalog.py` rules (M3 length table, bearing trade #) | 1.0 |
| 3 | `part_number` | SKU embedded in BOM text (`91290A120`) | 0.95 |
| 4 | `filtered_browse` | Metric fastener with category + browse root | 0.75 |
| 5 | `category_search` | Category route + `?searchQuery=` | 0.55 |
| 6 | `site_search` | Default `/products/standard-components/` | 0.35 |

Resolver entry point: `backend/services/vendors/mcmaster/tiers.py` → `resolve_mcmaster_link()`.

Legacy bridge: `mcmaster_handler.build_mcmaster_link()` delegates to the resolver.

## URL patterns

### Product (catalog / part number)

```
https://www.mcmaster.com/{partNumber}/?searchQuery={encodedQuery}
```

Built by `vendors/mcmaster/urls.py` → `mcmaster_product_url()`.

### Category search

```
https://www.mcmaster.com/products/screws/?searchQuery=M5+hex+bolt
```

Routes from `data/mcmaster_categories.json` via `classify_category()`.

### Filtered browse (Parse / live-site inspired)

McMaster encodes facets as **path segments**, not query parameters:

```
{categoryBrowseRoot}{facet~value/}…
```

**Example — M3 × 16 mm steel socket head cap screw (no catalog hit):**

```
https://www.mcmaster.com/products/screws/socket-head-screws-2~/steel-socket-head-screws~~/
  system-of-measurement~metric/
  thread-size~m3/
  length~16-mm/
  ?searchQuery=M3x16+socket+head+cap+screw
```

| BOM signal | Facet segment | Slug helper |
|------------|---------------|---------------|
| Metric | `system-of-measurement~metric/` | always for metric fasteners |
| M3 | `thread-size~m3/` | `metric_thread_filter_slug()` — M2.5 → `m2-5` |
| 16 mm length | `length~16-mm/` | `metric_length_filter_slug()` |

Browse roots (material finishes) live in `data/mcmaster_browse_roots.json`. When the BOM does not name a finish, the matcher attaches all applicable finish browse URLs on `Part.browse_finish_options` (black oxide, zinc plated, 18-8 stainless). When the BOM names a finish (`stainless`, `zinc plated`, `black oxide`, `alloy steel`), only that finish is offered.

Filter builders: `vendors/mcmaster/filters.py`, finish options: `vendors/mcmaster/finish_browse.py`.

## Official Product Information API (B2B)

Docs: [McMaster-Carr Product Information API](https://www.mcmaster.com/help/api/)

| Endpoint | Method | Use in this repo |
|----------|--------|------------------|
| `/v1/login` | POST | Bearer token (client cert required) |
| `/v1/products` | PUT | Subscribe + return product JSON |
| `/v1/products/{partNumber}` | GET | Specs, status, links |
| `/v1/products/{partNumber}/price` | GET | Price breaks |

Client: `backend/services/vendors/mcmaster/api.py` (re-exported from `mcmaster_api.py`).

**Important constraints from McMaster:**

- Requires approved account + PFX certificate (`eprocurement@mcmaster.com`).
- Must **subscribe** to each part (PUT) before GET — daily/total subscription limits apply.
- Tokens expire after 24h or logout.

When `MCMASTER_API_ENABLED=1`, the import pipeline calls `enrich_part_with_api()` after matching to fill:

- `mcmaster_detail_description`
- `mcmaster_product_status` (`Active`, `Discontinued`, …)
- `match_tier` → `api_verified`

API responses are **never** returned to the browser; guardrail tests scan for credential leaks.

### Mapping API specs to verification

API `Specifications[]` with `Attribute` / `Values` mirrors what Parse exposes as product `specs`. Future work: cross-check `hardware_spec.py` extractions against API attributes (Thread Size, Length, System of Measurement).

## Browse table resolution (optional live)

In-house Playwright scrape + parser (logic migrated from upstream [mcmaster-scraper](https://github.com/thedjchi/mcmaster-scraper) v0.2.1 — archived at `docs/archive/mcmaster-scraper-v0.2.1/`):

1. Load filtered browse URL with Playwright (`browse_scrape.fetch_product_presentations`).
2. Intercept `ProdPageWebPart.aspx` XHR (same endpoint the site uses for product tables).
3. Parse `ProductPresentations` JSON → `BrowseRow` list (`browse_parse.parse_product_presentations`).

| Module | Role |
|--------|------|
| `browse_scrape.py` | Playwright ProdPageWebPart JSON discovery |
| `browse_fetch.py` | Live fetch gate (`MCMASTER_BROWSE_RESOLVE_ENABLED=1`) |
| `browse_parse.py` | JSON → `BrowseRow` (fixtures + live path) |
| `scripts/mcmaster_browse_example.py` | Offline fixture / live browse demo |
| `notebooks/mcmaster_browse.ipynb` | Notebook walkthrough |
| `tests/fixtures/mcmaster_product_presentations_min.json` | Golden parse fixture |

Install: `pip install -e '.[playwright]' && playwright install chromium`

When browse resolve succeeds, `mcmaster_part_number` is filled from the table and confidence ≈ 0.9.

**Terms of use:** McMaster limits automated load to what is needed for purchasing decisions. Keep `RATE_LIMIT_OUTBOUND_MIN_INTERVAL`, disable browse in CI, and use curated catalog + offline filters by default.

## Part number extraction

`vendors/mcmaster/part_numbers.py`:

- Regex: `\b[0-9]{4,5}[A-Z][0-9]{2,3}\b`
- Used in tier 3 when makers paste SKUs in description/spec fields

## Data files

| File | Purpose |
|------|---------|
| `data/mcmaster_catalog.json` | Curated phrase → SKU |
| `data/mcmaster_categories.json` | Category routes + signals |
| `data/mcmaster_browse_roots.json` | Material-specific browse roots for filters |

Integrity: `scripts/check_catalog_integrity.py` (keys/titles vs rules).

## Matcher fields

After `match_part()`:

| Field | Set when |
|-------|----------|
| `mcmaster_url` | Always (unless `not_applicable`) |
| `mcmaster_part_number` | Catalog, rule, part_number, or browse resolve |
| `match_tier` | Winning offline/live tier |
| `hardware_match_status` | Post-match size/length verification |
| `mcmaster_detail_description` | API enrich |
| `mcmaster_product_status` | API enrich |

## Notebook / API parity

| Context | Offline tiers | API enrich | Browse resolve |
|---------|---------------|------------|----------------|
| `match_parts_only()` | Yes | No | No |
| `import_from_url` / `import_from_file` | Yes | If `MCMASTER_API_ENABLED` | If `MCMASTER_BROWSE_RESOLVE_ENABLED` |
| `04_match_mcmaster.ipynb` | Yes | No | No |

## Compare: three McMaster data sources

| Approach | Auth | Best for | This repo |
|----------|------|----------|-----------|
| **Official API** | Client cert + account | Production ERP, prices, CAD links | Optional `api.py` |
| **Public browse JSON** | None (browser session) | Discovering SKUs from filters | Optional `browse_fetch.py` |
| **Curated catalog + rules** | None | MVP, CI, predictable matching | Default |

Third-party wrappers (e.g. [Parse McMaster API](https://parse.bot/marketplace/01062b86-4335-4593-bd6a-23bb41400b48/mcmaster-com-api)) offer hosted search/filter/detail — we reimplemented the **filter URL grammar** and **table JSON shape** in-house to avoid external API keys and to keep the template self-contained.

## Module map

```
vendors/mcmaster/
├── urls.py           # mcmaster_product_url, filtered_browse_url
├── filters.py        # facet path segments
├── browse_roots.py   # load data/mcmaster_browse_roots.json
├── part_numbers.py   # SKU extraction
├── tiers.py          # resolve_mcmaster_link
├── browse_parse.py   # ProductPresentations → BrowseRow
├── browse_scrape.py  # Playwright ProdPageWebPart JSON fetch
├── browse_fetch.py   # Live fetch gate (MCMASTER_BROWSE_RESOLVE_ENABLED)
├── api.py            # Official REST client
└── enrichment.py     # pipeline post-match hook
```

Shims (stable imports): `mcmaster_catalog.py`, `mcmaster_handler.py`, `mcmaster_api.py`, `matcher.py`.
