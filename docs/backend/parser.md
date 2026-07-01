# Parser (`backend/services/parsers/spreadsheet/`)

Reads BOM files (CSV or XLSX) and converts rows into `Part` objects.

**Canonical module:** `backend/services/parsers/spreadsheet/csv_xlsx.py` (columns in `columns.py`)

**Legacy shim:** `backend/services/parser.py` re-exports the same API.

**Parser library:** [LIBRARY.md](../../backend/services/parsers/LIBRARY.md)

**Notebook:** `notebooks/03_parse_bom.ipynb`

---

## Constants

### `COLUMN_ALIASES`

Maps internal field names to recognized spreadsheet column headers. Matching is case-insensitive with underscores treated as spaces.

| Internal field | Recognized aliases |
|----------------|-------------------|
| `quantity` | `qty`, `quantity`, `count`, `amount`, `q'ty`, `qnty` |
| `name` | `name`, `part`, `part name`, `part_name`, `item`, `component`, `description`, `part description` |
| `specification` | `spec`, `specification`, `size`, `dimensions`, `details`, `notes`, `remark`, `remarks` |
| `notes` | `notes`, `comment`, `comments`, `extra` |

To support a new export format, add aliases here (prefer prototyping in the notebook first).

---

## `_normalize_column_name(col: str) -> str`

Normalizes a spreadsheet column header for comparison.

**Transformations**

- Strip whitespace
- Lowercase
- Replace `_` with space

**Example**

```python
_normalize_column_name("Part_Name")  # → "part name"
```

---

## `_map_columns(columns: list[str]) -> dict[str, str]`

Maps spreadsheet column headers to internal field names using `COLUMN_ALIASES`.

**Parameters**

- `columns` — list of column names from the DataFrame

**Returns** — dict mapping internal field → original column name

```python
# Input columns: ["Qty", "Part Name", "Specification"]
# Returns: {"quantity": "Qty", "name": "Part Name", "specification": "Specification"}
```

Only the first matching alias per field is used.

---

## `_read_dataframe(content: bytes, filename: str) -> pd.DataFrame`

Loads BOM bytes into a pandas DataFrame.

**Parameters**

- `content` — raw file bytes
- `filename` — used to determine file format from extension

**Format detection**

| Extension | Reader |
|-----------|--------|
| `.xlsx`, `.xls` | `pd.read_excel()` (requires `openpyxl`) |
| `.csv` | `pd.read_csv()` |
| Unknown | Tries CSV first, falls back to Excel |

---

## `dataframe_to_parts(df: pd.DataFrame) -> list[Part]`

Converts a DataFrame into a list of `Part` objects.

**Parameters**

- `df` — pandas DataFrame with BOM rows

**Returns** — list of `Part` (rows without a name are skipped)

**Behavior**

1. Map columns via `_map_columns`
2. If no `name` column is mapped, use the first non-quantity column as the name
3. For each row:
   - Parse `quantity` as float (defaults to `1.0` on missing or invalid values)
   - Read `original_name` from the name column (skip row if empty)
   - Read `specification` and `notes` if mapped
   - Set `normalized_name` equal to `original_name` (matcher updates this later)

**Skipped rows**

- Rows where the name field is empty or NaN
- Entirely empty rows are dropped before this function is called

---

## `parse_bom_bytes(content: bytes, filename: str) -> list[Part]`

**Main entry point.** Parses a BOM file from raw bytes.

**Parameters**

- `content` — raw BOM file bytes
- `filename` — filename with extension (e.g. `bom.csv`)

**Returns** — list of `Part` objects

**Steps**

1. `_read_dataframe(content, filename)`
2. Drop rows that are entirely NaN (`df.dropna(how="all")`)
3. `dataframe_to_parts(df)`

**Example**

```python
from pathlib import Path
from backend.services.parsers.spreadsheet import parse_bom_bytes
# Legacy: from backend.services.parser import parse_bom_bytes

parts = parse_bom_bytes(Path("data/sample_bom.csv").read_bytes(), "sample_bom.csv")
```
```
