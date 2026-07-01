# Pipeline (`backend/services/pipeline.py`)

Orchestrates the end-to-end import flow: scrape → parse → match.

**Notebook:** `notebooks/01_scrape.ipynb` … `05_api_payload.ipynb` (each stage maps to a function below)

---

## Stage functions (notebooks = API)

| Function | Stage(s) | Used by |
|----------|----------|---------|
| `scrape_makerworld(url, on_progress?)` | validate, scrape | notebooks 01–02, API import |
| `parse_bom_only(bytes, filename, on_progress?)` | parse_bom | notebook 03, API |
| `match_parts_only(parts, on_progress?)` | match_mcmaster | notebook 04, API |
| `parts_from_scrape_result(scrape)` | parse + match branch | API (embedded vs file) |
| `import_from_url(url, on_progress?)` | all stages | notebook 05, `POST /api/import` |
| `import_from_file(bytes, filename, ...)` | parse + match | `POST /api/import/file` |

---

## `import_from_url(url: str, on_progress?: ProgressCallback) -> Project`

**Main pipeline entry point.** Called by `POST /api/import` and `/import/stream`.

**Steps**

```
url
 └─► scrape_makerworld(url)
      ├─► title, description, thumbnail, bom_status, warnings
      └─► embedded parts OR bom_bytes + filename
           └─► parts_from_scrape_result OR parse_bom_only + match_parts_only
                └─► Project
```

If no BOM is found, returns a `Project` with `bom_status: "none"`, populated `warnings`, and empty `parts`.

---

## `import_from_file(content, filename, title?, on_progress?) -> Project`

Parse and match an uploaded spreadsheet (no MakerWorld scrape). Sets `bom_status: "upload"`.

---

## `scrape_makerworld(url, on_progress?) -> ScrapeResult`

Validate URL and run `scraper.scrape_project`. Emits SSE stage events when `on_progress` is provided.

---

## `parse_bom_only(content, filename, on_progress?) -> list[Part]`

Parse CSV/XLSX bytes via `parsers.spreadsheet.parse_bom_bytes` (no matching). Raises `ValueError` if no parts found.

---

## `match_parts_only(parts, on_progress?) -> list[Part]`

Run matcher + hardware size/length verification on an existing parts list.

---

## `parts_from_scrape_result(scrape: ScrapeResult, on_progress?) -> list[Part]`

Choose embedded parts (includes description BOM merged in scraper) or parse+match file BOM from a `ScrapeResult`.

---

## `parts_to_csv(parts: list) -> str`

Serializes a parts list to CSV text.

**Columns:** all `Part` model fields (`quantity`, `original_name`, `normalized_name`, `specification`, `notes`, `mcmaster_url`, `mcmaster_part_number`, `mcmaster_category`, `confidence`, `mcmaster_status`, `mcmaster_reason`, `hardware_diameter_mm`, `hardware_length_mm`, `hardware_match_status`)

**Used by:** `GET /api/bom/{project_id}/export`
