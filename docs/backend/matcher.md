# Matcher (`backend/services/matcher.py`)

Generates McMaster-Carr product URLs (catalog hits) or category-scoped search URLs, with confidence scores and hardware size/length verification.

**Notebook:** `notebooks/04_match_mcmaster.ipynb`

Catalog matches use `data/mcmaster_catalog.json` and `data/mcmaster_categories.json`. Post-match verification lives in `hardware_match_verify.py` (uses `hardware_spec.py`).

**Related:** `mcmaster_catalog.py`, `mcmaster_handler.py`

### Product URL pattern (catalog hits)

Confidence **1.0** when a catalog part number is resolved:

```
https://www.mcmaster.com/{partNumber}/?searchQuery={encodedQuery}
```

Example: `https://www.mcmaster.com/91290A120/?searchQuery=M3x16+mm+socket+head+cap+screw`

Search-only rows use category routes or **filtered browse** paths (metric thread + length facets), e.g.:

```
https://www.mcmaster.com/products/screws/socket-head-screws-2~/steel-socket-head-screws~~/system-of-measurement~metric/thread-size~m3/length~16-mm/?searchQuery=...
```

Plain category search example: `https://www.mcmaster.com/products/screws/socket-head-screws/?searchQuery=...`

Filtered browse facet names align with McMaster's public catalog filter model (documented in [McMaster adapter § Public catalog](mcmaster.md#public-catalog-navigation)).

See [McMaster adapter](mcmaster.md) for tier order and [Vendor adapters](vendors.md) for the cross-site template.

---

## Constants

| Name | Value | Purpose |
|------|-------|---------|
| `HARDWARE_KEYWORDS` | Compiled regex | Common hardware terms that boost confidence |

### `HARDWARE_KEYWORDS` pattern

Matches whole words (case-insensitive):

```
screw, bolt, nut, washer, bearing, spring, pin, rivet, standoff,
o-ring, seal, bushing, clamp, bracket, hinge, latch, magnet,
aluminum, steel, stainless, brass, nylon, delrin
```

---

## `normalize_hardware_name(name: str, specification: str = "") -> str`

Cleans a part name and specification into a search-friendly string.

**Parameters**

- `name` — part name from the BOM
- `specification` — optional spec string

**Returns** — cleaned search query

**Transformations**

1. Combine `name` and `specification` with a space
2. Collapse multiple whitespace to single spaces
3. Remove filler words: `printed`, `3d print`, `makerworld`, `optional`, `recommended`

**Example**

```python
normalize_hardware_name("3D printed bracket", "optional")
# → "bracket"
```

---

## `build_search_query(part: Part) -> str`

Builds the McMaster search query for a part.

**Parameters**

- `part` — `Part` with at least `original_name` (and optionally `specification`)

**Returns** — search query string

**Logic**

1. `primary_fastener_spec(part)` from `hardware_spec.py` — prefers `original_name` over polluted `specification`
2. If length is known, build explicit query (`M3x16 mm socket head cap screw`)
3. Otherwise `normalize_hardware_name(part.original_name, part.specification)`

```python
query = build_search_query(part)  # uses hardware_spec + normalize_hardware_name
```

---

## `score_confidence(part: Part, query: str) -> float`

Assigns a confidence score indicating how likely the query represents real purchasable hardware.

**Parameters**

- `part` — the part being matched
- `query` — the search query from `build_search_query`

**Returns** — float between `0.0` and `1.0` (rounded to 2 decimal places)

**Scoring**

| Signal | Points |
|--------|--------|
| Catalog hit (`catalog_lookup`) | **0.84 max** (was 1.0) — scored per candidate |
| Baseline (non-empty query) | +0.35 |
| `HARDWARE_KEYWORDS` match in query | +0.35 |
| `part.specification` is non-empty | +0.15 |
| Query contains a digit (e.g. M3, 8mm) | +0.10 |
| Query has 2+ words | +0.05 |

After matching, `hardware_match_verify` may lower confidence on `size_mismatch` / `length_mismatch` or restore **1.0** on `corrected`.

`resolve_match_status(confidence, preliminary, tier=…)` maps tier hints to editor status:

| Tier | Typical status |
|------|----------------|
| `catalog`, `rule`, `part_number`, `api_verified` | `likely` |
| `filtered_browse` | `likely` if confidence ≥ 0.65 else `possible` |
| `category_search` | `likely` if confidence ≥ 0.72 else `possible` |
| `not_applicable` | `not_applicable` — no McMaster link (includes unclassified hardware) |

Maximum score is capped at `1.0`.

**Example scores**

| Part | Query | Score |
|------|-------|-------|
| `M3-16 mm` + catalog hit | `M3x16 mm socket head cap screw` | **1.0** |
| `M3x8 Socket Head Cap Screw` + spec `Stainless` | (search) | ~0.85 |
| `Random 3D printed bracket` | `bracket` | ~0.40 |
| Empty name | `""` | 0.0 |

---

## `mcmaster_search_url(query: str) -> str`

Delegates to `build_mcmaster_link(query).url` — returns a product, filtered-browse, or category-scoped URL. Returns `""` when the line is unclassified or non-hardware (never McMaster Standard Components).

**Example**

```python
mcmaster_search_url("M3 socket head cap screw")
# → filtered browse or category URL under /products/screws/…

mcmaster_search_url("random widget bracket")
# → ""
```

---

## `match_part(part: Part) -> Part`

**Single-part entry point.** Ranks multiple McMaster candidates and picks the best guess; stores up to four alternatives on `Part.match_alternatives`.

**Flow**

1. `classify_mcmaster_eligibility` — skip filament, electronics, STL, etc.
2. `collect_scored_candidates` — generate catalog SKU, filtered browse, and category search guesses in parallel
3. Rank by confidence (filtered browse with metric thread + length beats catalog SKU for screws)
4. `verify_hardware_match` when primary is a catalog SKU
5. Attach `confidence_low` / `confidence_high` range on primary match

**Candidate ranking (typical metric screw)**

| Guess | Confidence | Notes |
|-------|------------|-------|
| Filtered browse (thread + length) | ~0.90 | Primary — pre-filtered McMaster table |
| Catalog / rule SKU | ~0.72–0.84 | Alternative — may be wrong material or head style |
| Category search | ~0.52 | Broader fallback |
| Unclassified | — | `not_applicable` — no URL (Standard Components excluded) |

Catalog hits no longer receive automatic **1.0** confidence.

**Returns** — `Part` with updated fields including `mcmaster_part_number`, `mcmaster_status`, `hardware_match_status`, `hardware_diameter_mm`, `hardware_length_mm`.

| Field | Set to |
|-------|--------|
| `normalized_name` | `build_search_query(part)` |
| `mcmaster_url` | Product or category search URL |
| `mcmaster_part_number` | Catalog SKU when matched |
| `confidence` | `1.0` on catalog hit, else heuristic score |
| `hardware_match_status` | `verified`, `corrected`, `size_mismatch`, etc. |

Original fields (`original_name`, `quantity`, etc.) are preserved via `model_copy`.

---

## `match_parts(parts: list[Part]) -> list[Part]`

**Batch entry point.** Applies `match_part` to every part in the list.

**Parameters**

- `parts` — list of parsed parts

**Returns** — list of matched parts (same length as input)

```python
from backend.models.part import Part
from backend.services.matcher import match_parts

matched = match_parts([
    Part(original_name="M3x8 screw", specification="Stainless"),
    Part(original_name="608ZZ bearing"),
])
```
