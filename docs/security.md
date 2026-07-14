# Security

Threat model and deployment guidance for the MakerWorld BOM → McMaster-Carr MVP.

**Design intent:** Local development tool (`./scripts/dev.sh`, localhost bind). The API has **no authentication**. Treat any network exposure beyond your machine as requiring the hardening steps below.

---

## Threat model

| Asset | Risk if exposed |
|-------|-----------------|
| In-memory projects (`/api/bom/{id}`) | Anyone with a UUID can read/write that BOM |
| Import/scrape proxy | Server fetches user-supplied MakerWorld URLs |
| McMaster outbound fetches | Server loads user-supplied `mcmaster_url` (browse, pricing sync) |
| Feedback dispatch | Optional email/GitHub/webhook spam when enabled |
| Debug endpoints | Pipeline logs and env hints when `DEBUG=1` |

---

## Current controls (working well)

| Control | Location |
|---------|----------|
| Credentials from env only | `backend/config.py` — never returned in API JSON |
| Guardrail tests | `tests/test_guardrails.py` — leak-bait scan on API responses + tracked files |
| Strict vendor URL hosts | `is_mcmaster_url` / `normalize_makerworld_url` — http(s) + hostname allowlist; reject private/link-local/loopback IP literals (`tests/test_urls.py`) |
| CORS defaults | `backend/main.py` — localhost origins unless `CORS_ORIGINS` overridden |
| Import rate limit | `POST /api/import*` — 12/min per client key |
| Feedback rate limit | `POST /api/feedback/match-error` — 10/min |
| Debug log gate | `GET /api/debug/logs` — 404 unless `DEBUG=1` |
| Feedback webhooks | URLs from `FEEDBACK_WEBHOOK_URLS` env only (not user input) |
| Dispatch off by default | `FEEDBACK_DISPATCH_ENABLED=False` |

Run guardrails in CI and before release:

```bash
pytest tests/test_guardrails.py -q
```

---

## Known gaps (July 2026 audit)

Prioritized for **public or shared-network** deployment. Acceptable for solo localhost use until fixed.

| Priority | Issue | Location | Mitigation |
|----------|-------|----------|------------|
| **Medium** | `POST /api/bom/sync-pricing` unauthenticated, uncapped | `bom_router.py` | Rate limit, max parts/request, re-validate URLs |
| **Medium** | Spoofable `X-Forwarded-For` for rate limits | `rate_limit.py` | Trust forwarded headers only from known reverse proxies |
| **Medium** | Unbounded upload `file.read()` | `import_router.py` | Max upload size (413) |
| **Medium** | No API auth | All routers | API key or OAuth before exposing beyond localhost |
| **Medium** | `javascript:` / `data:` in BOM link columns | `BomEditorPage.tsx` | Allow only `http:` / `https:` in `href` |
| **Medium** | BOM attachment download without host allowlist | `scraper.py` | Restrict download hosts to MakerWorld CDNs |
| **Medium** | Feedback dispatch abuse when enabled | `feedback_router.py` | Stricter limits, dedupe, optional shared secret |

Track remediation in [PLAN.md](../PLAN.md) Phase 10 — Security.

---

## Safe deployment checklist

Use this before binding to `0.0.0.0` or deploying to a shared host:

- [ ] Bind API to `127.0.0.1` unless behind an authenticated reverse proxy
- [ ] Set `CORS_ORIGINS` to your real frontend origin only
- [ ] Keep `DEBUG=0` in production
- [ ] Keep `FEEDBACK_DISPATCH_ENABLED=0` unless outbound channels are locked down
- [ ] Store McMaster API cert and feedback tokens in secrets manager / env — never commit
- [ ] Run `pytest tests/test_guardrails.py` in CI (see `.github/workflows/test.yml`)
- [x] Strict McMaster / MakerWorld hostname URL validation (substring SSRF fixed)
- [ ] Place reverse proxy in front and configure trusted `X-Forwarded-For` handling

---

## Outbound fetch boundaries

The server performs **server-side** HTTP/Playwright requests to:

| Target | Trigger |
|--------|---------|
| MakerWorld project pages | `POST /api/import` |
| MakerWorld BOM attachments | Scrape pipeline |
| McMaster browse URLs | Optional browse resolve, pricing sync, monthly taxonomy crawl |
| McMaster B2B API | Optional `MCMASTER_API_ENABLED` |
| GitHub / SMTP / webhooks | Optional feedback dispatch |

McMaster **monthly taxonomy crawl** is isolated to a scheduled GitHub Actions job with polite delays — not per-user import. See [McMaster taxonomy](backend/mcmaster-taxonomy.md).

---

## Reporting security issues

For this personal MVP repo, open a private note or GitHub security advisory if you deploy publicly and find an exploitable issue. Do not commit credentials, PFX files, or live API tokens.
