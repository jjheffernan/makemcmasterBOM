---
name: promote-notebook-to-service
description: >-
  Promotes validated notebook code into backend/services/ for the MakerWorld BOM
  app. Use when a notebook stage is stable and ready to move into FastAPI services
  or when refactoring duplicated logic between notebooks and services.
---

# Promote Notebook → Service

## Checklist

- [ ] Notebook runs end-to-end on at least one real MakerWorld project
- [ ] Edge cases documented in notebook markdown cell
- [ ] Function extracted with type hints and no notebook-only globals
- [ ] Placed in correct `backend/services/*.py` module
- [ ] Notebook updated to `from backend.services... import ...`
- [ ] `tests/` added for promoted logic
- [ ] API router calls service (not inline notebook code)

## Module map

- Scraping → `backend/services/scraper.py`
- MakerWorld parsers → `backend/services/parsers/makerworld/`
- Spreadsheet parsers → `backend/services/parsers/spreadsheet/`
- Shared parser helpers → `backend/services/parsers/helpers/` (see `LIBRARY.md`)
- McMaster links + verification → `backend/services/matcher.py`, `hardware_match_verify.py`
- Orchestration → `backend/services/pipeline.py`

Legacy shims (`description_bom.py`, `makerworld_bom.py`, `parser.py`, `hardware_terms.py`) re-export the new modules — prefer `backend.services.parsers.*` in new code.

## After promotion

Re-run `pytest` and the regression notebook (`05_api_payload.ipynb`) against sample URLs.
