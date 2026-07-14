# After-hours morning brief

**Run:** <startedAt ISO> → <stoppedAt ISO>
**Repo:** <owner/name> · **Base:** <baseBranch>
**Stop reason:** <done | blocked | noop | budget> · **Detail:** <empty-queue | maxPrs | guardrail | user-stop | consecutive-blocked | ci-red | preflight | dry-run | …>

## Summary

**Built (verified):** <n> · **Needs daylight:** <n> · **Verify-failed:** <n>

<!-- If megaPr: lead with MEGA-PR MODE banner — see references/mega-pr.md -->

<2–4 sentences: what ran, what shipped, what needs a human>

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

- <…>
- … or _None known_

## Suggested next

- Daytime alignment: <…>
- Ready queue: <…>
- Review: <…>

## Artifacts

- State: `.cursor/after-hours-loop.state.json` (or configured `statePath`)
- Config: `.cursor/after-hours-loop.config.json` (if used)
- Runs: `<runsPath>/` (if configured)
