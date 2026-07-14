# State schema (version 1)

Persistent loop state at config `statePath`, default `.cursor/after-hours-loop.state.json`. Gitignore the file.

Optional check: `scripts/validate-state.py <statePath>` (exit 0 = ok).

## Top-level fields

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `version` | `1` | yes | Schema version; bump only on breaking change |
| `startedAt` | ISO-8601 | yes | Loop run start |
| `stoppedAt` | ISO-8601 | no | Set on stop |
| `stopReason` | string | no | Coarse domain-agnostic enum: `done` \| `blocked` \| `noop` \| `budget` |
| `stopDetail` | string | no | Optional specifics (legacy detail strings): `empty-queue`, `maxPrs`, `guardrail`, `user-stop`, `consecutive-blocked`, `ci-red`, `preflight`, `dry-run`, … |
| `sources` | array | yes | Parsed Sources entries `{ type, config }` |
| `queue` | array | yes | Work items (see below) |
| `prs` | object[] | yes | Outcomes that produced PRs this run: `{ "url", "itemId", "branch", "draft" }` (`url` required; others when known). `maxPrs` counts `prs.length`. Empty when no `draft-pr` outcomes. |
| `maxPrs` | number | yes | Cap from bootstrap / config (limits `draft-pr` outcomes; other adapters ignore this cap unless noted) |
| `tick` | number | yes | Completed tick count (0 after bootstrap before first completion is ok) |
| `priority` | string | yes | `github-first` \| `fifo` \| `todo-first` |
| `baseBranch` | string | yes | Default base for git/PR outcome adapters |
| `dryRun` | boolean | no | If true, this run must not write state (see dry-run) |
| `consecutiveBlocked` | number | no | Successive `blocked`/`skipped` without an intervening `done`; see counter rules below |
| `megaPr` | boolean | no | **This run only.** `true` only after bootstrap validated both kickoff tokens ([mega-pr.md](./mega-pr.md)). Default absent/`false`. Never copy from config or prior nights. |

## Queue item contract (portable)

Every work item is a **tracker-agnostic** unit. Portable fields (use these names going forward):

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `id` | string | yes | Stable id: `{source}:{stable-key}` e.g. `github:52` |
| `title` | string | yes | Short label |
| `acceptance` | string | preferred | Testable criteria / Brief excerpt; empty → likely `blocked` at readiness |
| `blockerPolicy` | string | no | How to treat incomplete work: `block` (default) \| `skip` \| `defer`. Maps onto overnight skip/block choices in [guardrails.md](./guardrails.md). |
| `executorHint` | string | no | Preferred executor id (`pr-slice`, `feature-build`, `research-only`, `docs-digest`, `ops-checklist`, …). If omitted, derive from `executor` or Sources defaults. |
| `outcomeKind` | string | no | Outcome adapter after completion — [outcomes.md](./outcomes.md). Defaults: code executors → `draft-pr`; `docs-digest` → `doc-artifact`; `ops-checklist` → `report-only`. Overrides: `branch-only`, `report-only`, `external-ticket-update`, … |
| `verification` | string[] | no | Commands that must succeed before `done` (from Agent Brief / spec / Sources). Empty → fall back to config `testCommand` when the executor requires tests. See [readiness.md](./readiness.md). |
| `risk` | string | no | `low` \| `medium` \| `high`. Default `medium` when omitted. High-risk items: tighter overnight behavior ([guardrails.md](./guardrails.md)). |

These fields are **independent of GitHub/PR**. Sources may fill them from issues, TODOs, specs, maps, or future non-code queues.

## Work item fields (full v1 + aliases)

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | Portable — see above |
| `title` | string | Portable |
| `acceptance` | string | Portable |
| `blockerPolicy` | string | Portable; optional |
| `executorHint` | string | Portable alias / preference for executor |
| `outcomeKind` | string | Portable; see [outcomes.md](./outcomes.md) |
| `source` | string | Adapter that materialized the item: `github-issues`, `todo-md`, `feature-spec`, … |
| `executor` | string | Bound executor for this run; prefer matching `executorHint` when set |
| `ref` | string | URL, path, or other locator in the origin tracker |
| `granularity` | string | `single-pr` \| `multi-slice` (legacy names; means single vs multi outcome unit) |
| `status` | string | `open` \| `in-progress` \| `done` \| `blocked` \| `skipped` |
| `blockReason` | string | optional: `needs-info`, `needs-grill`, `tests`, `hitl`, … — detail when `status` is `blocked`/`skipped` |
| `parentId` | string | optional: umbrella parent for child slices |
| `notes` | string | optional: short residual note **and** non-PR outcome records (`doc-artifact: <path>`, `branch-only: after-hours/…`, `report-only: …`, `external-ticket-update: <comment url|id>`) |
| `verification` | string[] | optional: see portable contract |
| `risk` | string | optional: `low` \| `medium` \| `high` |

### Field name map (old ↔ portable)

| Portable / preferred | Existing / alias | Notes |
|----------------------|------------------|-------|
| `id`, `title`, `acceptance` | same | Unchanged |
| `executorHint` | `executor` | Sources may set either; runtime binds `executor` for the tick |
| `outcomeKind` | (new) | Default `draft-pr` for code executors; omit → inherit executor default |
| `blockerPolicy` | `blockReason` + guardrail choice | Policy = how to treat unreadiness; `blockReason` = why after the fact |
| `verification` | (new) | Prefer Brief / spec `verification:` lists; else config `testCommand` |
| `risk` | (new) | Default `medium`; omit → treat as medium |
| `source`, `ref`, `status`, `granularity`, `parentId`, `notes` | same | Keep; tracker-specific, not PR-specific |

Backward-compatible: existing state JSON without `outcomeKind` / `blockerPolicy` / `executorHint` remains valid. Infer `outcomeKind: draft-pr` for `pr-slice` / `feature-build` / `research-only`; `docs-digest` → `doc-artifact`; `ops-checklist` → `report-only`.

## Stop reasons (coarse + detail)

On stop, persist **`stopReason`** (coarse) and optionally **`stopDetail`** (specifics). Morning brief shows both when useful.

| `stopReason` | Meaning | Typical `stopDetail` |
|--------------|---------|----------------------|
| `done` | Run ended after intentional completion / human stop | `user-stop` |
| `blocked` | Stopped because work/safety cannot continue | `consecutive-blocked`, `guardrail`, `preflight`, `ci-red` |
| `noop` | Nothing executable / dry inspection only | `empty-queue`, `dry-run` |
| `budget` | Hit a run budget | `maxPrs` |

Always set coarse `stopReason`. Prefer also setting `stopDetail` to the legacy-specific string. Readers that only understand old single-field values may treat unknown coarse enums via `stopDetail` when present.

## `consecutiveBlocked` counter

| When | Action |
|------|--------|
| Bootstrap / new run | Set `consecutiveBlocked` to `0` |
| Item → `blocked` or `skipped` | Increment by 1; write state |
| Item → `done` | Reset to `0`; write state |
| After increment | If `consecutiveBlocked >= maxConsecutiveBlocked` (config; default `3`) → **stop loop**; `stopReason: blocked`, `stopDetail: consecutive-blocked`; morning brief ([guardrails.md](./guardrails.md)) |

Umbrella parents finishing as terminal without a child `done` this streak still count as blocked/skipped for the counter when that parent is marked blocked/skipped.

## Claim / in-progress

1. Claim = set `status` to `in-progress` and **write state** before side effects.
2. Only one non-child item `in-progress` at a time (children: one active child).
3. On success: `done`; run [outcome adapter](./outcomes.md) for `outcomeKind`; append to `prs` when adapter is `draft-pr`; for non-PR adapters record path / branch / comment / findings in item `notes` (and [cloud ledger](./cloud-ledger.md) when enabled); clear claim; **reset `consecutiveBlocked` to `0`**.
4. On fail soft: `blocked` or `skipped` with `blockReason`; clear claim; **increment `consecutiveBlocked`** (then check stop threshold).
5. Never leave the working tree dirty *and* forget to persist status.

## Resume mid-queue

1. On tick start, load state if present and `startedAt` matches this armed run (or same-night Automation continuation with same Sources intent).
2. Prefer resume: finish `in-progress` item first, then next `open` by priority.
3. Do not re-queue IDs already `done` / `blocked` / `skipped` this run unless Sources refresh proves the human re-opened agent-ready work **and** id was cleared — default: preserve outcomes.
4. Umbrella `multi-slice` parent stays `open` until all children are terminal (`done` / `blocked` / `skipped`).
5. **Cloud Automation:** if `statePath` is missing (typical when gitignored), treat as a **new bootstrap**. Skip items already covered by an open draft PR / prior adapter artifact (title/body/branch references the item id). When `cloudLedgerPath` is set, also apply [cloud-ledger.md](./cloud-ledger.md). Do not invent prior queue status.

## Dry-run does not write state

When `/after-hours --dry-run` or message `dryRun: true`:

- Build and print the queue (and readiness notes).
- Do **not** create or update `statePath`.
- Do **not** open PRs, edit product files, or arm a coding tick.
- Optional: print what stop would be — `stopReason: noop`, `stopDetail: dry-run`.

See [bootstrap.md](./bootstrap.md).

## Executor binding

When materializing / claiming an item:

1. If `executorHint` or `executor` is set → bind that module (`executors/<id>.md`).
2. `docs-digest` when hint/name is `docs-digest` (or Sources line names it); default `outcomeKind: doc-artifact`.
3. `ops-checklist` when hint/name is `ops-checklist`; default `outcomeKind: report-only` (`doc-artifact` when Sources ask for a durable file).
4. `research-only` stays the research-with-optional-PR path — do not auto-replace with `docs-digest` / `ops-checklist`.
5. Else derive from source defaults (`pr-slice`, `feature-build`, …).
