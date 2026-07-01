# API reference

Base URL (development): `http://localhost:8000`

The frontend calls these endpoints via relative paths (`/api/...`) proxied through Vite.

Interactive docs are available at [http://localhost:8000/docs](http://localhost:8000/docs) when the server is running (FastAPI auto-generated OpenAPI).

## Rate limiting

When `RATE_LIMIT_ENABLED=1` (default), all `POST /api/import*` endpoints are limited per client IP (default **12 requests/minute**). Excess requests return **429** with a `Retry-After` header.

Outbound MakerWorld fetches are throttled separately (min interval + max concurrent scrapes) — this does not surface as an API error but slows imports under load.

`GET /api/health` reports the active rate-limit settings. See [Development](development.md#environment-variables).

---

## `GET /api/health`

Health check and runtime config summary.

**Response** `200`

```json
{
  "status": "ok",
  "debug": false,
  "rate_limit": {
    "enabled": true,
    "import_per_minute": 12,
    "outbound_min_interval_sec": 1.0,
    "max_concurrent_scrapes": 2
  }
}
```

---

## `GET /api/import/stages`

List pipeline stages (used by the import UI progress bar). **Not rate limited.**

**Response** `200`

```json
{
  "stages": [
    { "id": "validate", "label": "Validate URL" },
    { "id": "scrape", "label": "Scrape MakerWorld" }
  ]
}
```

---

## `POST /api/import`

Import a MakerWorld project: scrape page, extract BOM, parse parts, generate McMaster links.

**Request body**

```json
{
  "url": "https://makerworld.com/en/models/12345-example"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | yes | MakerWorld project URL |

**Response** `200`

```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "project": {
    "title": "Example Project",
    "makerworld_url": "https://makerworld.com/en/models/12345-example",
    "description": "Project description from page metadata",
    "thumbnail_url": "https://...",
    "bom_status": "embedded",
    "warnings": [],
    "parts": [ /* Part objects */ ]
  }
}
```

| `bom_status` | Meaning |
|--------------|---------|
| `embedded` | Parts from MakerWorld `__NEXT_DATA__` JSON |
| `description` | Parts parsed from project description (BOM section keywords) |
| `file` | Parts parsed from a downloaded CSV/XLSX attachment |
| `upload` | Parts parsed from a user-uploaded file (`POST /api/import/file`) |
| `none` | No BOM found — import succeeds with empty `parts` and `warnings` |

**Errors**

| Status | Cause |
|--------|-------|
| `400` | Invalid URL (not a makerworld.com link) |
| `429` | Import rate limit exceeded |
| `502` | Scrape or download failure |

**Handler:** `import_router.import_project` → `pipeline.import_from_url`

---

## `POST /api/import/stream`

Same as `POST /api/import` but returns **Server-Sent Events** with per-stage progress.

**Request body** — same as `POST /api/import`

**Response** `200` — `text/event-stream`

Event types:

| `type` | Payload |
|--------|---------|
| `stage` | `{ "type": "stage", "stage": "scrape", "status": "running", "message": "..." }` |
| `complete` | `{ "type": "complete", "project_id": "...", "project": { ... } }` |
| `error` | `{ "type": "error", "detail": "...", "status": 400 \| 502 }` |

When `DEBUG=1`, stage events may include a `debug` object; error events include `traceback`.

**Errors:** `429` before the stream starts if rate limited.

---

## `POST /api/import/file`

Import from an uploaded BOM file (skip MakerWorld scrape).

**Request** — `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | yes | CSV or XLSX BOM |
| `title` | string | no | Project title (defaults to filename) |

**Response** `200` — same shape as `POST /api/import` (`bom_status: "upload"`)

**Errors:** `400`, `429`, `502`

---

## `POST /api/import/file/stream`

SSE variant of file import. Same multipart body as `POST /api/import/file`.

---

## `GET /api/bom/{project_id}`

Retrieve a previously imported project.

**Response** `200` — `Project` object (see [models](models.md))

**Errors**

| Status | Cause |
|--------|-------|
| `404` | Unknown `project_id` |

**Handler:** `bom_router.get_bom`

---

## `PUT /api/bom/{project_id}`

Update the parts list for a project (user edits from the BOM editor).

**Request body**

```json
{
  "parts": [
    {
      "quantity": 4,
      "original_name": "M3x8 Socket Head Cap Screw",
      "normalized_name": "M3x8 Socket Head Cap Screw Stainless",
      "specification": "Stainless Steel",
      "notes": "",
      "mcmaster_url": "https://www.mcmaster.com/91290A120/?searchQuery=M3x16+mm+socket+head+cap+screw",
      "mcmaster_part_number": "91290A120",
      "mcmaster_category": "socket_head_screw",
      "confidence": 1.0,
      "mcmaster_status": "likely",
      "mcmaster_reason": "Catalog match — M3 × 16 mm Socket Head Screw",
      "match_tier": "catalog",
      "mcmaster_detail_description": "",
      "mcmaster_product_status": "",
      "hardware_diameter_mm": 3,
      "hardware_length_mm": 16,
      "hardware_match_status": "verified"
    }
  ]
}
```

**Response** `200` — updated `Project` object

**Errors**

| Status | Cause |
|--------|-------|
| `404` | Unknown `project_id` |

**Handler:** `bom_router.update_bom`

---

## `GET /api/bom/{project_id}/export`

Download the current parts list as CSV.

**Response** `200`

- Content-Type: `text/csv`
- Content-Disposition: `attachment; filename="{title}.csv"`

**Errors**

| Status | Cause |
|--------|-------|
| `404` | Unknown `project_id` |

**Handler:** `bom_router.export_csv` → `pipeline.parts_to_csv`

---

## `GET /api/notebooks`

List pipeline development notebooks for the web UI.

**Response** `200`

```json
{
  "notebooks": [
    {
      "filename": "01_scrape.ipynb",
      "title": "01 — Scrape MakerWorld",
      "description": "Download project page, extract metadata, locate BOM attachment.",
      "stage": "scrape",
      "jupyter_path": "notebooks/01_scrape.ipynb"
    }
  ],
  "jupyter_url": "/jupyter/lab/tree/notebooks"
}
```

**Handler:** `notebooks_router.list_notebooks`

---

## Debug endpoints (`DEBUG=1`)

| Endpoint | Description |
|----------|-------------|
| `GET /api/debug` | Debug status (always reachable; returns `"debug": false` when off) |
| `GET /api/debug/logs` | Recent pipeline/scrape log entries (404 when debug off) |
| `DELETE /api/debug/logs` | Clear log buffer (404 when debug off) |

See [Development — Debug mode](development.md#debug-mode).
