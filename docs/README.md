# Documentation

Reference documentation for the MakerWorld BOM → McMaster-Carr generator.

## Guides

| Document | Description |
|----------|-------------|
| [Architecture](architecture.md) | System overview, data flow, and repository layout |
| [Development](development.md) | Local setup, dev scripts, environment variables |
| [Notebooks](notebooks.md) | Pipeline notebooks and notebook-driven workflow |
| [Testing](testing.md) | Running tests and what they cover |
| [Parsers](backend/parsers.md) | Site-specific BOM parser layout and imports |
| [Feedback dispatch](backend/feedback-dispatch.md) | Email, GitHub issues, and webhooks for bug reports |
| [McMaster taxonomy](backend/mcmaster-taxonomy.md) | Category data files, monthly crawl, department routing |
| [Security](security.md) | Threat model, audit findings, deployment checklist |

## Reference

| Document | Description |
|----------|-------------|
| [API](api.md) | HTTP endpoints, request/response shapes, error codes |
| [Data models](models.md) | `Part` and `Project` schemas |
| [Frontend](frontend.md) | React pages and API client functions |
| [Style guide](style-guide.md) | CSS tokens, colors, typography (MakerWorld + McMaster) |

## Backend services

Each service module owns one stage of the import pipeline. Functions are documented in detail:

| Module | Document | Stage |
|--------|----------|-------|
| `backend/services/scraper.py` | [Scraper](backend/scraper.md) | Download MakerWorld page and BOM file |
| `backend/services/parsers/` | [Parsers](backend/parsers.md) · [LIBRARY.md](../backend/services/parsers/LIBRARY.md) | Site parsers + helpers |
| `backend/services/parsers/spreadsheet/` | [Parser](backend/parser.md) | CSV/XLSX → `Part` |
| `backend/services/matcher.py` | [Matcher](backend/matcher.md) | McMaster links + size/length verification |
| `backend/services/vendors/` | [Vendor adapters](backend/vendors.md) · [McMaster](backend/mcmaster.md) | Tiered supplier linking (template for other sites) |
| `backend/services/pipeline.py` | [Pipeline](backend/pipeline.md) | Orchestrate scrape → parse → match |
| `backend/rate_limit.py` | [Architecture — Rate limiting](architecture.md#rate-limiting) | API import limits + outbound MakerWorld throttling |
| `backend/api/store.py` | [Store](backend/store.md) | In-memory project persistence (MVP) |

## Quick links

- [Execution plan](../PLAN.md) — phased delivery status and backlog
- [Security](security.md) — deployment and known gaps
- [Data files](../data/README.md) — McMaster routing JSON reference
- [Archives](archive/README.md) — superseded planning and upstream scraper reference
