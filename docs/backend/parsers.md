# Parsers (`backend/services/parsers/`)

Site-specific BOM parsers and shared helpers. Full API reference: **[LIBRARY.md](../../backend/services/parsers/LIBRARY.md)** in the repo.

## Layout

```
parsers/
  helpers/          # hardware_signals, bom_quantities, bom_line, quantity_checks, …
  makerworld/       # description, embedded, page_json
  spreadsheet/      # columns, csv_xlsx
```

## Canonical imports

```python
# MakerWorld embedded + description BOM
from backend.services.parsers.makerworld import (
    parts_from_design,
    parts_from_description,
    extract_design,
    extract_next_data,
)

# Uploaded / downloaded spreadsheets
from backend.services.parsers.spreadsheet import parse_bom_bytes

# Shared hardware keyword library
from backend.services.parsers.helpers.hardware_signals import has_hardware_signal
```

## Legacy shims (still valid)

| Shim | Points to |
|------|-----------|
| `backend.services.description_bom` | `parsers.makerworld.description` |
| `backend.services.makerworld_bom` | `parsers.makerworld.page_json` + `embedded` |
| `backend.services.parser` | `parsers.spreadsheet` |
| `backend.services.hardware_terms` | `parsers.helpers.hardware_signals` |

Prefer `parsers.*` in new code and notebooks.

## CLI check scripts

| Script | Purpose |
|--------|---------|
| `scripts/parse_description_bom.py` | Parse description BOM to JSON |
| `scripts/check_bom_quantities.py` | Flag qty stuck in specification |
| `scripts/check_hardware_specs.py` | Flag size/length mismatch vs catalog |

## Notebooks

| Notebook | Parser module |
|----------|---------------|
| `02_extract_bom.ipynb` | `parsers.makerworld.description` |
| `03_parse_bom.ipynb` | `parsers.spreadsheet` |
