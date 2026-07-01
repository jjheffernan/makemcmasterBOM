# Scraper (`backend/services/scraper.py`)

Downloads MakerWorld project pages, extracts embedded BOM data, and locates file attachments.

**Related modules:** `page_fetch.py` (HTTP/Playwright), `parsers/makerworld/` (`__NEXT_DATA__` + description BOM), `rate_limit.py` (outbound throttling)

**Notebook:** `notebooks/01_scrape.ipynb`, `notebooks/02_extract_bom.ipynb`

---

## Constants

| Name | Value | Purpose |
|------|-------|---------|
| `MAKERWORLD_BASE` | `https://makerworld.com` | Base domain reference |

HTTP headers live in `http_client.BROWSER_HEADERS` (browser-like User-Agent to avoid 403).

---

## `ScrapeResult`

```python
@dataclass
class ScrapeResult:
    title: str
    description: str
    makerworld_url: str
    thumbnail_url: str
    bom_bytes: bytes | None
    bom_filename: str | None
    bom_content_type: str | None
    embedded_parts: list[Part]
    bom_status: BomStatus
    warnings: list[str]
```

Return type for `scrape_project`. Contains page metadata, optional file BOM, and/or embedded parts from `__NEXT_DATA__`.

| Field | Description |
|-------|-------------|
| `title` | Project title |
| `description` | Project description |
| `makerworld_url` | Normalized input URL |
| `thumbnail_url` | OG image URL when present |
| `bom_bytes` | Raw BOM file content, or `None` |
| `bom_filename` | Filename from download URL |
| `bom_content_type` | HTTP `Content-Type` from BOM download |
| `embedded_parts` | Parts parsed from page JSON (Maker's Supply, filaments, etc.) |
| `bom_status` | `"embedded"`, `"file"`, or `"none"` |
| `warnings` | Non-fatal issues (e.g. no BOM found) |

---

## `normalize_makerworld_url(url: str) -> str`

Validates and normalizes a MakerWorld project URL.

**Raises** `ValueError` if not a `makerworld.com` link.

---

## `fetch_page(url: str) -> str`

Downloads HTML via `page_fetch.fetch_makerworld_html` (rate-limited).

**Behavior**

- `SCRAPER=auto` — httpx first, Playwright fallback on 403/429/proxy errors
- `SCRAPER=playwright` — headless Chromium only
- `SCRAPER=httpx` — HTTP only
- Retries with exponential backoff (`tenacity`)

---

## BOM extraction

### Embedded (`parsers/makerworld/embedded.py`, `page_json.py`)

Primary path for modern MakerWorld projects:

1. Parse `#__NEXT_DATA__` JSON from HTML
2. Extract `design` object
3. Build `Part` list from `boms_v2`, filament entries, and `boms_of_other_part_list`

### File attachment

Fallback when spreadsheet links are present:

1. `_find_bom_link(soup, page_url)` scans anchors for BOM labels or `.csv`/`.xlsx`/`.xls` extensions
2. `download_bom(url)` fetches the file (rate-limited)

**Ranking signals:** BOM label (+10), `.csv` (+5), `.xlsx` (+3)

---

## `download_bom(url: str) -> tuple[bytes, str, str | None]`

Downloads a BOM file from a direct URL inside `outbound_request()` (rate-limited).

**Returns** — `(file_bytes, filename, content_type)`

---

## `scrape_project(url: str, on_progress: ...) -> ScrapeResult`

**Main entry point.** Orchestrates the full scrape for a MakerWorld project.

**Steps**

1. `normalize_makerworld_url(url)`
2. `fetch_page(url)` → parse with BeautifulSoup
3. Extract title, description, thumbnail
4. `extract_next_data` + `parts_from_design` for embedded BOM
5. If no embedded parts, `_find_bom_link` + optional `download_bom`
6. Set `bom_status` and `warnings`; return `ScrapeResult`

**Note:** Missing BOM is not an error — `bom_status: "none"` with warnings; pipeline continues with empty parts unless embedded data exists.
