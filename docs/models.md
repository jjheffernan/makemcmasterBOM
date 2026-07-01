# Data models

Pydantic models in `backend/models/`. The frontend mirrors these shapes in `frontend/src/lib/api.ts`.

---

## `Part`

Represents one hardware line item from a BOM.

**Source:** `backend/models/part.py`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `quantity` | `float` | `1` | Number of units needed |
| `original_name` | `str` | `""` | Part name as it appeared in the source BOM |
| `normalized_name` | `str` | `""` | Cleaned name used for McMaster search (set by matcher) |
| `specification` | `str` | `""` | Size, material, or other details from the BOM |
| `notes` | `str` | `""` | Free-form notes (from BOM or user edits) |
| `mcmaster_url` | `str` | `""` | McMaster-Carr product or search URL (set by matcher) |
| `mcmaster_part_number` | `str` | `""` | Catalog SKU when matched (e.g. `91290A120`) |
| `mcmaster_category` | `str` | `""` | McMaster category route id (e.g. `socket_head_screw`) |
| `confidence` | `float` | `0.0` | Match confidence score, `0.0`–`1.0` (set by matcher) |
| `mcmaster_status` | `str` | `"possible"` | `likely`, `possible`, `unlikely`, or `not_applicable` |
| `mcmaster_reason` | `str` | `""` | Human-readable match note or eligibility reason |
| `match_tier` | `str` | `""` | Resolution tier: `catalog`, `rule`, `part_number`, `filtered_browse`, `category_search`, `site_search`, `api_verified` |
| `mcmaster_detail_description` | `str` | `""` | Product detail from official API when enabled |
| `mcmaster_product_status` | `str` | `""` | API status (`Active`, `Discontinued`, …) |
| `hardware_diameter_mm` | `float \| null` | `null` | Parsed metric diameter (e.g. `3` for M3) |
| `hardware_length_mm` | `float \| null` | `null` | Parsed fastener length in mm |
| `hardware_match_status` | `str` | `"unchecked"` | Size/length verification: `verified`, `corrected`, `size_mismatch`, `length_mismatch`, `spec_conflict`, `length_unknown`, `unchecked`, `not_applicable` |

### Field lifecycle

```
BOM row  →  parsers/* set quantity, original_name, specification, notes
         →  matcher sets normalized_name, mcmaster_url, mcmaster_part_number, confidence
         →  hardware_match_verify sets hardware_* fields and hardware_match_status
         →  user may edit any field in the BOM editor
```

`original_name` is never overwritten by the matcher. It preserves the source data for traceability.

---

## `Project`

Represents an imported MakerWorld project with its parsed parts.

**Source:** `backend/models/project.py`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `title` | `str` | `""` | Project title from page metadata |
| `makerworld_url` | `str` | `""` | Normalized MakerWorld project URL |
| `description` | `str` | `""` | Project description from page metadata |
| `thumbnail_url` | `str` | `""` | Project thumbnail from OG image metadata |
| `parts` | `list[Part]` | `[]` | Parsed and matched hardware items |
| `bom_status` | `"file" \| "embedded" \| "description" \| "none" \| "upload"` | `"none"` | How the BOM was obtained |
| `warnings` | `list[str]` | `[]` | Non-fatal import issues (shown in UI banner) |

### `bom_status` values

| Value | Meaning |
|-------|---------|
| `embedded` | Parts from `__NEXT_DATA__` on the MakerWorld page |
| `description` | Parts parsed from project description prose (`parsers/makerworld/description.py`) |
| `file` | Parts parsed from a downloaded CSV/XLSX attachment |
| `upload` | Parts from a user-uploaded file |
| `none` | No BOM found — `parts` is empty |

### Example

```json
{
  "title": "Linear Rail Actuator",
  "makerworld_url": "https://makerworld.com/en/models/12345",
  "description": "A compact linear actuator using GT2 belt drive.",
  "thumbnail_url": "https://makerworld.bblmw.com/makerworld/model/...",
  "bom_status": "embedded",
  "warnings": [],
  "parts": [
    {
      "quantity": 4,
      "original_name": "M3x8 Socket Head Cap Screw",
      "normalized_name": "M3x8 Socket Head Cap Screw Stainless Steel",
      "specification": "Stainless Steel",
      "notes": "MakerWorld BOM (description)",
      "mcmaster_url": "https://www.mcmaster.com/91290A120/?searchQuery=M3x16+mm+socket+head+cap+screw",
      "mcmaster_part_number": "91290A120",
      "mcmaster_category": "socket_head_screw",
      "confidence": 1.0,
      "mcmaster_status": "likely",
      "mcmaster_reason": "Catalog match — M3 × 16 mm Socket Head Screw (Socket Head Screws)",
      "hardware_diameter_mm": 3,
      "hardware_length_mm": 16,
      "hardware_match_status": "verified"
    }
  ]
}
```

---

## Confidence scores

The matcher assigns `confidence` based on catalog hits, heuristics, and post-match verification (see [Matcher](backend/matcher.md)):

| Range | Meaning |
|-------|---------|
| `1.0` | Catalog part-number match (`data/mcmaster_catalog.json`) with verified size/length |
| `≥ 0.70` | Strong hardware signal — `mcmaster_status: likely` |
| `0.40`–`0.69` | Moderate — review recommended (`possible`) |
| `< 0.40` | Weak or size/length mismatch (`unlikely` / lowered after verify) |

`hardware_match_status` records verification: `verified`, `corrected`, `size_mismatch`, `length_mismatch`, `spec_conflict`, `length_unknown`, `unchecked`, `not_applicable`.

The frontend displays confidence as a percentage with color coding (green / amber / red).
