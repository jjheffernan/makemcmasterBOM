# Frontend

React application in `frontend/`. Built with Vite, Tailwind CSS v4, and shadcn-style UI components.

## Routes

| Path | Component | Purpose |
|------|-----------|---------|
| `/` | `ImportPage` | MakerWorld URL input and import trigger |
| `/bom/:projectId` | `BomEditorPage` | Editable parts table (engineer-density sticky toolbar) |
| `/notebooks` | `NotebooksPage` | Pipeline notebook catalog + JupyterLab embed |
| `/settings` | `SettingsPage` | Matching preferences (localStorage; exact/lazy guess, etc.) |

Routing is handled by `react-router-dom` in `src/App.tsx`.

### Matching preferences (client)

`frontend/src/lib/matchPreferences.ts` (when merged) persists:

| Pref | Values | Default |
|------|--------|---------|
| `guess_mode` | `exact` \| `lazy` | `lazy` (current matcher behavior) |
| `prefer_length_filter` | bool | `true` |
| `show_wider_scope_alternatives` | bool | `true` |

Backend `match_parts(..., guess_mode=)` honors `exact` by suppressing `wider_scope` alternatives (see `tests/test_guess_mode.py`).

### Export

BOM editor exports via `GET /api/bom/{id}/export` (CSV default; TSV/XLSX via `?format=` when export-pack lands). Prefer a single Export control with format choices for density.
---

## Matching preferences (`src/lib/matchPreferences.ts`)

Browser-local prefs (key `makerworld-bom-match-prefs`):

| Key | Values | Default | Effect today |
|-----|--------|---------|--------------|
| `guess_mode` | `exact` \| `lazy` | `lazy` | Persisted only — no rematch API yet (slice F) |
| `prefer_length_filter` | bool | `true` | Persisted only until backend honors it |
| `show_wider_scope_alternatives` | bool | `true` | BOM Link column hides “Wider search” when false |

`matchPreferencesForApi()` returns the same fields for a future rematch/import options request. Unset storage uses the defaults above so matching behavior matches pre-Settings imports.

---

## API client (`src/lib/api.ts`)

Typed `fetch` wrappers for all backend endpoints. All requests use relative `/api/...` paths (proxied to FastAPI in development).

### Types

| Interface | Mirrors |
|-----------|---------|
| `Part` | `backend.models.part.Part` |
| `Project` | `backend.models.project.Project` |
| `ImportResponse` | `POST /api/import` response |
| `NotebookInfo` | Single notebook metadata |
| `NotebooksResponse` | `GET /api/notebooks` response |

### `importProject(url: string): Promise<ImportResponse>`

Posts a MakerWorld URL to `POST /api/import`.

**Parameters**

- `url` — MakerWorld project URL

**Returns** — `{ project_id, project }`

**Throws** — `Error` with server `detail` message on failure

**Used by:** `ImportPage` — on success, navigates to `/bom/{project_id}`

---

### `getProject(projectId: string): Promise<Project>`

Fetches a project from `GET /api/bom/{projectId}`.

**Used by:** `BomEditorPage` — loads project if not passed via navigation state

---

### `updateProject(projectId: string, parts: Part[]): Promise<Project>`

Saves edited parts via `PUT /api/bom/{projectId}`.

**Parameters**

- `projectId` — UUID from import
- `parts` — full updated parts array

**Used by:** `BomEditorPage` — "Save" button

---

### `exportCsvUrl(projectId: string): string`

Returns the download URL for `GET /api/bom/{projectId}/export`.

**Used by:** `BomEditorPage` — "Export CSV" link (`<a download>`)

---

### `listNotebooks(): Promise<NotebooksResponse>`

Fetches notebook catalog from `GET /api/notebooks`.

**Used by:** `NotebooksPage` via TanStack Query (`useQuery`)

---

## Pages

### `ImportPage`

- URL text input with HTML5 `type="url"` validation
- Submit calls `importProject`
- Shows loading spinner during import
- Displays server error messages
- Redirects to BOM editor on success

### `BomEditorPage`

- Loads project from navigation state or `getProject` API
- Renders editable table with TanStack Table
- Editable columns: quantity, part name, specification, McMaster URL, notes
- McMaster column: status badge (`Likely` / `Verify` / `Unlikely` / `N/A`), reason text, `match_tier` label, hardware verification note
- **Verify banner** when rows need manual McMaster confirmation (`possible` / `unlikely` / confidence &lt; 70%)
- Highlighted rows for parts that need verification
- Confidence displayed as color-coded percentage (read-only)
- External link icon opens McMaster URL in new tab; catalog SKU shown under link
- Delete row button per row
- **Column resize** — drag the right edge of a header (TanStack Table `columnResizeMode: onChange`)
- **Bulk edit** — checkbox column; toolbar to set quantity on selected rows or delete selected
- **Section headings** — editable group titles; drag handle to reorder parts within a section
- **Hardware check hints** — `?` tooltips with per-family verification checklists (`hardwareCheckTips.ts`)
- **Finish dropdown** — in the **Specification** column when multiple McMaster finishes apply (black oxide, zinc plated, stainless)
- **Other guesses** — grouped dropdown in the Link column (same-size vs wider-scope alternatives; wider group respects Settings)
- **Pricing tab** — pack-aware line totals when listing prices are synced
- **Report error** — flag wrong matches; optional reporter email
- **Match column** — status badge + confidence + tier (compact layout)
- Save persists via `updateProject` (includes optional `bom_headings`)
- Export CSV via direct download link

External links (`mcmaster_url`, `makerworld_url`) open in a new tab. Validate `http(s)` only before public deployment — see [Security](security.md).

See `src/lib/mcmaster.ts` for status/tier label helpers.

### `SettingsPage`

- Dense form for matching prefs (guess mode, length-filtered browse, wider-scope alts)
- Writes immediately to localStorage via `matchPreferences.ts`
- Nav link in `Layout` header

### `NotebooksPage`

- Lists pipeline notebooks from API with stage badges
- "Open JupyterLab" button links to proxied JupyterLab
- Per-notebook "Open" links to specific `.ipynb` files
- Embedded iframe showing JupyterLab at `/jupyter/lab/tree/notebooks`

---

## UI components (`src/components/ui/`)

shadcn-style components built with `class-variance-authority` and Tailwind:

| Component | File | Purpose |
|-----------|------|---------|
| `Button` | `button.tsx` | Primary actions; exports `buttonVariants` for styled links |
| `Input` | `input.tsx` | Text and number fields in table cells |
| `Card` | `card.tsx` | Page sections with header, title, description, content |
| `Table` | `table.tsx` | BOM data table structure |

Utility: `cn()` in `src/lib/utils.ts` merges Tailwind classes via `clsx` + `tailwind-merge`.

---

## Dev proxy (`vite.config.ts`)

| Path | Target | Purpose |
|------|--------|---------|
| `/api` | `http://127.0.0.1:8000` | Backend API |
| `/jupyter` | `http://127.0.0.1:8888` | JupyterLab (WebSocket enabled) |

The `/jupyter` rewrite strips the prefix so JupyterLab receives requests at its root.
