# Site adapters (design-host ingestion)

This package scaffolds **multi-site BOM ingestion** under `backend/services/sites/`. Today only **MakerWorld** is registered and wired as a thin wrapper over the existing scraper/parser. Printables, Thingiverse, and other hosts are **not** implemented — stub comments only.

## Scaffold-only status

| What | Status |
|------|--------|
| `SiteAdapter` protocol | Present (`base.py`) |
| `MakerWorldAdapter` | Wraps `scraper.scrape_project` + `parser.parse_bom_bytes` |
| Registry URL lookup | Ready via `get_adapter_for_url` |
| Live API / pipeline routing | **Unchanged** — default import still uses MakerWorld-specific paths |
| Printables / Thingiverse / etc. | **Not built** — comments in `registry.py` only |

Do **not** expect other marketplaces to scrape or parse until a later slice lands a live adapter and optionally routes the API through the registry.

## Package layout

```
backend/services/sites/
├── __init__.py      # Public exports
├── base.py          # SiteAdapter protocol (site_id, can_handle, scrape, parse_bom)
├── makerworld.py    # MakerWorldAdapter
└── registry.py      # register + get_adapter_for_url; Future stubs
```

## Adding another site (later)

1. Implement `<site>.py` with `site_id`, `can_handle`, `scrape`, and `parse_bom`.
2. `register(...)` in `registry.py` (or keep bootstrap explicit).
3. Add offline `can_handle` / registry tests — **no live network in default CI**.
4. Only then consider routing `pipeline` / API through `get_adapter_for_url`.

## Relation to vendor adapters

- **Sites** (`services/sites/`) — where the BOM *comes from* (MakerWorld, …).
- **Vendors** (`services/vendors/`) — where line items *link for purchase* (McMaster, …).

See [vendors.md](vendors.md) for the supplier-side pattern this mirrors.
