# Run evidence artifacts

Optional per-tick evidence so mornings can see **what was verified**, not only what was claimed done.

## Config

| Key | Default | Meaning |
|-----|---------|---------|
| `runsPath` | `null` (off) | Directory for one short record per completed item/tick. Example: `.cursor/after-hours-runs/` |

When `null` / unset: do not write run files — state + morning brief only.

Prefer gitignoring run dirs (session noise). Cloud Automation: evidence survives only if you commit the dir or paste summaries into the brief / PR body.

## Record shape

Write `<runsPath>/<itemId-safe>-<tick>.md` (or `.json`) after each terminal item attempt:

```markdown
# Run evidence — <itemId>

- **at:** <ISO-8601>
- **status:** done | blocked | skipped
- **blockReason:** <if any>
- **verification:** <commands run; exit codes; or "none listed — used testCommand">
- **outcome:** <pr url | doc path | branch | report-only | none>
- **notes:** <one line>
```

Never paste secrets, `.env` bodies, or full log dumps — pointers and exit codes only.

## Orchestrator duties

1. After executor + outcome adapter (or on block/skip), if `runsPath` is set, write the record.
2. Link the directory from the morning brief **Artifacts** section.
3. On verification failure: set `blockReason: verification-failed` (or `tests`) and still write evidence when `runsPath` is set.
