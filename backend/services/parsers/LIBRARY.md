# Parser library

Site-specific BOM parsers live under `backend/services/parsers/`. Shared logic is extracted into `helpers/` so new sites can reuse quantity parsing, hardware detection, and section scanning without copying regex.

## Directory layout

```
backend/services/parsers/
  LIBRARY.md              ← this document
  __init__.py
  helpers/                ← site-agnostic functions
    hardware_signals.py
    html_text.py
    bom_quantities.py
    bom_sections.py
    bom_line.py
    marketplace.py
    parts_merge.py
  makerworld/               ← MakerWorld.com
    page_json.py
    embedded.py
    description.py
  spreadsheet/              ← uploaded CSV / XLSX files
    columns.py
    csv_xlsx.py
```

Legacy import paths (`description_bom`, `makerworld_bom`, `parser`, `hardware_terms`) remain as thin re-export shims.

---

## Helpers (`parsers/helpers/`)

### `hardware_signals.py`

Shared vocabulary and regex for recognizing catalog hardware in free text. Used by description parsers, the McMaster matcher, and catalog lookup.

| Symbol | Kind | Purpose |
|--------|------|---------|
| `METRIC_SIZES` | `tuple[str]` | Known metric labels: M2–M12 |
| `METRIC_THREAD_RE` | `Pattern` | `M3`, `M2.5`, etc. |
| `METRIC_FASTENER_RE` | `Pattern` | `M3x8`, `M3×8mm`, `M3-16` |
| `IMPERIAL_THREAD_RE` | `Pattern` | `#6-32`, `1/4-20` |
| `DIMENSION_AXIAL_RE` | `Pattern` | `5x30`, `8×22×7`, `12/10mm` |
| `LENGTH_MM_RE`, `LENGTH_CM_RE`, `LENGTH_IN_RE` | `Pattern` | Unit lengths |
| `BEARING_DESIGNATION_RE` | `Pattern` | `608-ZZ`, `693RS` |
| `FASTENER_TYPES`, `FASTENER_PREFIXES` | `frozenset` | Word lists for screws, nuts, etc. |
| `HARDWARE_TERMS` | `frozenset` | Broader BOM vocabulary |
| `HARDWARE_KEYWORD_RE` | `Pattern` | Compiled union of `HARDWARE_TERMS` |
| `HARDWARE_KEYWORDS` | alias | Back-compat name for `HARDWARE_KEYWORD_RE` |

| Function | Returns | Purpose |
|----------|---------|---------|
| `has_fastener_type(text)` | `bool` | Screw/bolt/nut/washer/etc. |
| `has_fastener_prefix(text)` | `bool` | Hex, socket, button, … |
| `has_fastener_suffix(text)` | `bool` | Ends with a fastener type word |
| `has_metric_size(text)` | `bool` | Standalone M-label |
| `has_metric_fastener(text)` | `bool` | Thread × length |
| `has_imperial_thread(text)` | `bool` | Imperial thread callout |
| `has_length_mm/cm/in(text)` | `bool` | Length with unit |
| `has_axial_dimension(text)` | `bool` | `5x30`-style dimensions |
| `has_bearing_designation(text)` | `bool` | Bearing part numbers |
| `has_hardware_keyword(text)` | `bool` | Any term in `HARDWARE_TERMS` |
| `has_hardware_signal(text)` | `bool` | **Composite** — true if any hardware signal matches |
| `extract_metric_sizes(text)` | `list[str]` | Normalized M-labels found in text |

**Import:** `from backend.services.parsers.helpers.hardware_signals import has_hardware_signal`

---

### `html_text.py`

| Function | Returns | Purpose |
|----------|---------|---------|
| `html_to_text(html)` | `str` | HTML → plain text with paragraph breaks |
| `collapse_blank_lines(text)` | `str` | Collapse 3+ newlines to 2 |
| `collapse_inline_whitespace(text)` | `str` | Collapse runs of spaces/tabs |

---

### `bom_quantities.py`

Parses quantity prefixes/suffixes on a single BOM line.

| Symbol | Purpose |
|--------|---------|
| `BULLET_PREFIX`, `NUMBER_PREFIX` | Strip `-`, `1.`, `2)` list markers |
| `QTY_LEADING` | `4x M3 screw` |
| `QTY_TRAILING` | `M3 screw x4` |
| `QTY_EXPLICIT` | `qty: 4 - M3 screw` |
| `QTY_PCS` | `4pcs` / `min 4pcs` |

| Function | Returns | Purpose |
|----------|---------|---------|
| `strip_line_prefix(line)` | `str` | Remove bullet/number prefix |
| `parse_quantity_and_name(line)` | `(float, str, str, str)` | Quantity, name, specification, context_note |

Leading `Nx` is not applied when the remainder looks like a bare dimension (`5x30`) unless it also contains a hardware keyword (screw, bearing, etc.).

---

### `bom_sections.py`

| Function | Purpose |
|----------|---------|
| `find_section_lines(text, *, section_start, section_stop, expand_line=None)` | Collect lines under a BOM header until a stop header. Optional `expand_line` splits long inline prose (MakerWorld `Parts:` blocks). |

Site parsers supply their own `section_start` / `section_stop` regex patterns.

---

### `bom_line.py`

| Function | Returns | Purpose |
|----------|---------|---------|
| `parse_hardware_line(line, *, default_notes, require_hardware_signal=True, clean_name=None)` | `Part \| None` | Full single-line parse: quantity, marketplace cleanup, optional hardware filter, `Part` construction |

`clean_name` is an optional site-specific name normalizer (MakerWorld strips `Amazon.de`, `DIY & Tools`, etc.).

---

### `marketplace.py`

| Symbol / function | Purpose |
|-------------------|---------|
| `MARKETPLACE_NOISE` | Regex for trailing Amazon/AliExpress/etc. |
| `SKIP_PROSE_LINE` | Skip author commentary lines |
| `strip_marketplace_tokens(block)` | Remove tokens that break colon parsing |
| `clean_name_and_spec(name, spec)` | Trim marketplace suffixes; truncate very long names |
| `marketplace_note_suffix(line, base_note)` | Append marketplace hint to `Part.notes` |

---

### `parts_merge.py`

| Function | Purpose |
|----------|---------|
| `merge_parts(*lists)` | Combine multiple `list[Part]`; first occurrence wins on `(name, quantity)` |

---

### `quantity_checks.py`

Runtime validation for misparsed quantities (e.g. `13 x M3-16 mm` stuck in specification).

| Function | Purpose |
|----------|---------|
| `check_parsed_line(line)` | Validate raw line against `parse_quantity_and_name` |
| `check_part(part, *, index=0, source_line=None)` | Flag `qty_in_specification`, `hardware_in_specification`, etc. |
| `check_parts(parts, *, source_lines=None)` | Validate a part list |
| `format_issues(issues)` | Human-readable report |

CLI: `scripts/check_bom_quantities.py` (exit 1 when issues found).

---

## Matcher verification (outside `parsers/`)

Post-match size/length checks live next to the matcher (not in site parsers):

| Module | Purpose |
|--------|---------|
| `backend/services/hardware_spec.py` | Extract metric diameter/length from BOM text |
| `backend/services/hardware_match_verify.py` | Verify catalog hit vs BOM; auto-correct mismatches |

CLI: `scripts/check_hardware_specs.py`

`Part.hardware_match_status`: `verified`, `corrected`, `size_mismatch`, `length_mismatch`, `spec_conflict`, `length_unknown`, `unchecked`, `not_applicable`

---

## Site parsers

### MakerWorld — `parsers/makerworld/`

#### `page_json.py`

Extract structured data from MakerWorld HTML.

| Function | Returns | Purpose |
|----------|---------|---------|
| `extract_next_data(html)` | `dict \| None` | Parse `__NEXT_DATA__` script JSON |
| `extract_design(next_data)` | `dict \| None` | `pageProps.design` object |

#### `embedded.py`

BOM rows embedded in the design JSON.

| Function | Returns | Purpose |
|----------|---------|---------|
| `parts_from_design(design)` | `list[Part]` | Maker's Supply, materials, filament, other-parts lists |
| `find_attachment_urls(design, page_url)` | `list[tuple[str, str]]` | CSV/XLSX download URLs in the JSON tree |
| `score_attachment(url, filename)` | `int` | Rank attachments (BOM keyword, file type) |
| `best_attachment(candidates)` | `tuple \| None` | Highest-scoring attachment |

#### `description.py`

Rule-based parsing of project description prose (no LLM).

| Function | Returns | Purpose |
|----------|---------|---------|
| `normalize_prose(text)` | `str` | Fix run-on MakerWorld HTML/text before parsing |
| `resolve_description_text(soup_html, design)` | `str` | Pick richest description source |
| `description_summary(text, max_len=220)` | `str` | UI preview; stops before `Parts:` |
| `find_bom_section_lines(text)` | `list[str]` | Section-header BOM lines |
| `extract_candidate_lines(description)` | `(list[str], bool)` | Section, inline `Parts:`, or fallback scan |
| `parse_bom_line(line, *, require_hardware_keyword=True)` | `Part \| None` | MakerWorld-specific line wrapper |
| `parts_from_description(description)` | `list[Part]` | End-to-end description BOM |
| `merge_parts` | — | Re-exported from `helpers.parts_merge` |

MakerWorld-specific regex (`SECTION_START`, `INLINE_PARTS_BLOCK`, `PROSE_PCS_TERMINATOR`, etc.) stays in this module.

**Import:**

```python
from backend.services.parsers.makerworld import parts_from_design, parts_from_description
```

---

### Spreadsheet — `parsers/spreadsheet/`

Uploaded BOM files (not tied to a single site).

#### `columns.py`

| Symbol / function | Purpose |
|-------------------|---------|
| `COLUMN_ALIASES` | Maps logical fields (`quantity`, `name`, `specification`, `notes`) to header aliases |
| `normalize_column_name(col)` | Lowercase, spaces for underscores |
| `map_columns(columns)` | `dict[str, str]` logical → actual column name |

#### `csv_xlsx.py`

| Function | Purpose |
|----------|---------|
| `parse_bom_bytes(content, filename)` | Read CSV/XLSX bytes → `list[Part]` |
| `dataframe_to_parts(df)` | `pandas.DataFrame` → `list[Part]` |

**Import:**

```python
from backend.services.parsers.spreadsheet import parse_bom_bytes
```

---

## Adding a new site

1. Create `backend/services/parsers/<site>/`.
2. Reuse helpers: `parse_hardware_line`, `find_section_lines`, `has_hardware_signal`, `html_to_text`, `merge_parts`.
3. Keep site-specific regex and JSON field names in the site package only.
4. Wire the scraper to call the new parser; add fixtures and tests under `tests/`.
5. Optionally add a backward-compat shim at `backend/services/<site>_bom.py`.

---

## Backward-compatible import paths

| Legacy module | New location |
|---------------|--------------|
| `backend.services.hardware_terms` | `parsers.helpers.hardware_signals` |
| `backend.services.description_bom` | `parsers.makerworld.description` |
| `backend.services.makerworld_bom` | `parsers.makerworld.page_json` + `embedded` |
| `backend.services.parser` | `parsers.spreadsheet` |
