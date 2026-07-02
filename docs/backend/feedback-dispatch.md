# Feedback dispatch

When a user submits **Report an error** from the BOM editor, the API always appends to `data/match_reports.jsonl`. Optional outbound dispatch fans the same report to email, GitHub, and webhooks.

## Enable

Set in `.env`:

```bash
FEEDBACK_DISPATCH_ENABLED=1
```

Then enable one or more channels below. Disabled channels are skipped; API responses still succeed if local persistence works.

## Channels

| Channel | Env flags | Notes |
|---------|-----------|-------|
| **Email** | `FEEDBACK_EMAIL_ENABLED`, SMTP vars, `FEEDBACK_EMAIL_TO` | Uses stdlib SMTP. Sets `Reply-To` when `reporter_email` is present on the report. |
| **GitHub** | `FEEDBACK_GITHUB_ENABLED`, `FEEDBACK_GITHUB_TOKEN`, `FEEDBACK_GITHUB_REPO` | Creates an issue via REST API. Labels from `FEEDBACK_GITHUB_LABELS` (default `bug,match-report`). |
| **Webhooks** | `FEEDBACK_WEBHOOK_ENABLED`, `FEEDBACK_WEBHOOK_URLS` | Comma-separated POST URLs. Discord webhook URLs get an embed payload; others receive generic JSON. |

## API response

`POST /api/feedback/match-error` returns:

```json
{
  "id": "…",
  "reported_at": "…",
  "message": "Thank you — your report was saved. We've notified the maintainers.",
  "dispatch": [
    { "channel": "github", "ok": true, "detail": "issue #42", "url": "https://github.com/…" },
    { "channel": "email", "ok": true, "detail": "sent to you@example.com", "url": "" }
  ]
}
```

Channel failures appear in `dispatch` with `ok: false` but do not fail the HTTP request.

## Implementation

| Module | Role |
|--------|------|
| `backend/routers/feedback_router.py` | Persist report, call dispatcher |
| `backend/services/feedback/dispatcher.py` | Orchestration |
| `backend/services/feedback/formatters.py` | Titles and bodies |
| `backend/services/feedback/email_channel.py` | SMTP |
| `backend/services/feedback/github_channel.py` | GitHub Issues API |
| `backend/services/feedback/webhook_channel.py` | HTTP POST fan-out |

## Discord example

```bash
FEEDBACK_WEBHOOK_ENABLED=1
FEEDBACK_WEBHOOK_URLS=https://discord.com/api/webhooks/ID/TOKEN
```

## Matrix / other bridges

Most Matrix→HTTP bridges accept the generic JSON payload:

```json
{
  "event": "match_error_report",
  "title": "[McMaster report] Wrong McMaster part # — M3x8 …",
  "message": "…",
  "github_issue_url": "https://github.com/…"
}
```

Point `FEEDBACK_WEBHOOK_URLS` at your bridge URL. If the bridge needs a custom shape, add a formatter branch in `webhook_channel.py`.

## Tests

```bash
pytest tests/test_feedback_dispatch.py -q
```

Uses `pytest-httpx` to mock GitHub and webhook HTTP; SMTP is not exercised in CI.
