# Store (`backend/api/store.py`)

In-memory project storage for the MVP. Projects are lost when the server restarts.

There is no database, authentication, or cross-session persistence in the current version.

---

## `save(project: Project) -> str`

Stores a new project and returns its ID.

**Parameters**

- `project` — `Project` to store

**Returns** — UUID string (e.g. `"550e8400-e29b-41d4-a716-446655440000"`)

**Called by:** `import_router.import_project` after a successful import

---

## `get(project_id: str) -> Project | None`

Retrieves a project by ID.

**Parameters**

- `project_id` — UUID returned from `save`

**Returns** — `Project` if found, `None` if not

**Called by:** `bom_router.get_bom`, `bom_router.update_bom`, `bom_router.export_csv`

---

## `update(project_id: str, project: Project) -> bool`

Replaces a stored project.

**Parameters**

- `project_id` — UUID of the project to update
- `project` — new `Project` value

**Returns**

- `True` — project was updated
- `False` — `project_id` not found

**Called by:** `bom_router.update_bom`

---

## Implementation notes

Storage is a module-level dictionary:

```python
_store: dict[str, Project] = {}
```

This is intentionally simple for MVP validation. A future version would replace this with a database or file-backed store without changing the function signatures used by routers.
