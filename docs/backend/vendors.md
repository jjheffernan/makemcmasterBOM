# Vendor adapters (supplier enrichment)

This project links BOM lines to **supplier sites** through a small **vendor adapter** layer under `backend/services/vendors/`. McMaster-Carr is the first implementation; copy the same shape when adding DigiKey, Mouser, Grainger, etc.

## Why a vendor layer?

MakerWorld ingestion (`parsers/makerworld/`) is **site-specific**. McMaster matching is also **site-specific**, but we keep it separate because:

1. The same BOM `Part` may link to multiple suppliers later.
2. Each supplier has different URL patterns, optional official APIs, and browse-table JSON.
3. Notebooks and the API should call **one tiered resolver** per vendor, not ad-hoc URL string building.

```
BOM Part  →  normalize query  →  vendor.tiers.resolve_*  →  VendorLink
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              static catalog    filtered browse    official API
              (offline JSON)  (public site URL)  (B2B credentials)
```

## Package layout (template)

```
backend/services/vendors/
├── base.py                 # VendorLink, VendorMatchContext, VendorAdapter protocol
└── <vendor_id>/
    ├── urls.py             # Product + category + filtered browse URL builders
    ├── filters.py          # Map BOM specs → site facet path segments
    ├── part_numbers.py     # Extract SKUs from text/URLs
    ├── browse_roots.json   # (data/) Category material routes for filtered browse
    ├── browse_parse.py     # Parse supplier browse JSON → rows (offline)
    ├── browse_fetch.py     # Optional live fetch (@integration)
    ├── api.py              # Optional official REST client
    ├── tiers.py            # Tiered offline resolution
    └── enrichment.py       # Post-match API / browse enrichment (async)
```

### Adding a new supplier

1. Copy `vendors/mcmaster/` → `vendors/<new_vendor>/`.
2. Implement `resolve_<vendor>_link()` with your tier order (catalog → rules → browse → search).
3. Add `data/<vendor>_catalog.json` and `data/<vendor>_categories.json` if needed.
4. Wire the matcher stage (or a multi-vendor orchestrator) to call your resolver.
5. Document tiers in `docs/backend/<vendor>.md`.
6. Add offline tests — **never require live network in default CI**.

## Shared contracts (`base.py`)

| Type | Purpose |
|------|---------|
| `VendorMatchContext` | Normalized query + source `Part` |
| `VendorLink` | Resolved URL, `link_kind`, `match_tier`, optional SKU |
| `MatchTier` | Which layer produced the link (`catalog`, `filtered_browse`, …) |
| `VendorAdapter` | Protocol for `build_link` + optional `enrich_link` |

`Part.match_tier` stores the winning tier on each BOM row for UI and debugging.

## Pipeline integration

| Stage | Module | Network |
|-------|--------|---------|
| Offline match | `matcher.match_part` → `vendors/mcmaster/tiers.py` | No |
| API enrich | `pipeline._maybe_enrich_parts` → `enrichment.py` | Optional B2B API |
| Browse resolve | `enrichment.try_resolve_part_from_browse` | Optional Playwright |

Notebooks call `match_parts_only()` (offline tiers only). The website import stream also runs `_maybe_enrich_parts()` when API or browse flags are enabled.

## McMaster reference

See [McMaster adapter](mcmaster.md) for tier details, filter URL grammar, official API mapping, and browse-table parsing.

## External references (not dependencies)

We **do not** install these packages; we studied their approaches:

| Source | What we adopted |
|--------|-----------------|
| [McMaster Product Information API](https://www.mcmaster.com/help/api/) | B2B client in `vendors/mcmaster/api.py` — login, subscribe, specs, price |
| [mcmaster-scraper](https://github.com/thedjchi/mcmaster-scraper) | Archived at `docs/archive/mcmaster-scraper-v0.2.1/` — Playwright logic migrated to `browse_scrape.py`; parser in `browse_parse.py` |
| [Parse McMaster API](https://parse.bot/marketplace/01062b86-4335-4593-bd6a-23bb41400b48/mcmaster-com-api) | Search → filters → product detail flow; inspired facet naming |

## Configuration

| Variable | Default | Effect |
|----------|---------|--------|
| `MCMASTER_FILTERED_BROWSE_ENABLED` | `1` | Tier 4 filtered path URLs (offline) |
| `MCMASTER_BROWSE_RESOLVE_ENABLED` | `0` | Live browse table → part number |
| `MCMASTER_API_ENABLED` | `0` | Official API enrichment |

See [Development](../development.md#mcmaster-vendor-settings) for credential variables.

## Testing

- `tests/test_mcmaster_vendor.py` — filters, tiers, browse JSON fixture, API payload parse
- `tests/test_mcmaster_handler.py` / `test_mcmaster_catalog.py` — integration with matcher
- Live browse: mark `@pytest.mark.integration` only (not in default CI)

```bash
pytest tests/test_mcmaster_vendor.py -v
```
