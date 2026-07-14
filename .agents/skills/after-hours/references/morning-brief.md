# Morning brief

Durable handoff for the human after a stop. Write **on every stop** (`noop` / `budget` / `blocked` / `done` — any stop path).

## Path

| Source | Path |
|--------|------|
| Config `morningBriefPath` | Use that value |
| Default | `.cursor/after-hours-morning-brief.md` |

Copyable body: [templates/morning-brief.md](../templates/morning-brief.md).

## Pass-report triad (first-class)

Map item outcomes into these human sections (in addition to storage statuses):

| Section | Includes |
|---------|----------|
| **Built (verified)** | `done` items that ran verification (or had none required) and published their outcome |
| **Needs daylight** | `blocked`/`skipped` with `needs-info`, `needs-grill`, `hitl`, or high-risk skip |
| **Verify-failed** | `blocked` with `verification-failed` / `tests` / `ci-red` |

Keep Done / Blocked / Skipped rows for ids; lead Summary with triad counts.

## Template

```markdown
# After-hours morning brief

**Run:** <startedAt ISO> → <stoppedAt ISO>
**Repo:** <owner/name> · **Base:** <baseBranch>
**Stop reason:** <done | blocked | noop | budget> · **Detail:** <empty-queue | maxPrs | guardrail | user-stop | consecutive-blocked | ci-red | preflight | dry-run | …>

## Summary

**Built (verified):** <n> · **Needs daylight:** <n> · **Verify-failed:** <n>

<2–4 sentences: what ran, what shipped, what needs a human>

<!-- If state.megaPr: lead with: **MEGA-PR MODE** — human opted in this run via CONFIRM_MEGA_PR. Bundled draft — review carefully. -->

## Built (verified)

- `<id>` — <outcome pointer>
- … or _None_

## Needs daylight

- `<id>` — **why:** <needs-info | needs-grill | hitl | high-risk | …> · **human must:** <concrete next step>
- … or _None_

## Verify-failed

- `<id>` — **why:** <verification-failed | tests | ci-red> · **human must:** <concrete next step>
- … or _None_

## PRs opened

- <title> — <url> (draft)
- … or _None_

## Doc / non-PR outcomes

- `<id>` — `doc-artifact:` <path>
- … or _None_

## Done

- `<id>` — <one-line outcome>
- … or _None_

## Blocked

- `<id>` — **why:** <…> · **human must:** <…>
- … or _None_

## Skipped

- `<id>` — <why>
- … or _None_

## Residual risk

- <manual checks, flaky tests, partial migrations, review focus>
- … or _None known_

## Suggested next

- Daytime alignment: <what to clarify tomorrow, if any>
- Ready queue: <what to label / brief before next AFK>
- Review: <which PR or digest to look at first>

## Artifacts

- State: `.cursor/after-hours-loop.state.json` (or configured `statePath`)
- Config: `.cursor/after-hours-loop.config.json` (if used)
- Runs: `<runsPath>/` (if configured — [run-artifacts.md](./run-artifacts.md))
```

## Writing rules

1. **Pointers > dumps** — PR URLs, issue links, file paths, item IDs. No pasted secret material, `.env` bodies, tokens, or full logs.
2. **Redact** — replace credentials with `<redacted>`; mention path only if relevant to residual risk.
3. **Every stop** — overwrite or update the brief file even if no PRs opened (empty night / doc-only night still useful).
4. **Blocked must be actionable** — each blocked row needs *why* + *what the human must do*.
5. **Suggested next** — prefer daytime alignment, Agent Brief, label `ready-for-agent`. Do not pretend AFK will fix fog.
6. Keep Summary short; put detail in triad / Done / Blocked.
7. **Stop line** — show coarse `stopReason`; include `stopDetail` when set ([state-schema.md](./state-schema.md)).
8. **Mega-PR** — if state `megaPr: true`, lead Summary with the MEGA-PR MODE banner ([mega-pr.md](./mega-pr.md)) and list every bundled item.
9. **Triad honesty** — never put verify-failed items under Built (verified).
