# Outcome adapters

Executors produce a **completion signal** (`done` / `blocked` / `skipped`) plus a requested **outcome adapter**. They do **not** “must open a PR” — PRs are one adapter among others.

**A→Z** = executor-defined completion for the item (acceptance satisfied) **plus** a successful (or intentional no-op) outcome adapter — not solely “opened a PR.” See [glossary](../docs/glossary.md).

Wire via queue field `outcomeKind` ([state-schema.md](./state-schema.md)). Sources or executor defaults may set it; bootstrap may leave it unset → executor default applies.

## Contract

| Step | Who | Responsibility |
|------|-----|----------------|
| 1. Execute | Executor (`executors/*.md`) | Complete A→Z work for the item; emit completion signal |
| 2. Publish | Outcome adapter (this doc) | Persist the shippable artifact (PR, branch, doc path, report, external update) |
| 3. Record | Orchestrator | Update item `status`; append adapter-specific records (`prs` for `draft-pr`; path / branch / comment in `notes` for others; ledger when enabled) |

An item is **`done`** when the executor’s acceptance work is complete **and** the requested adapter succeeds (or is intentionally no-op). Adapter failure without a recoverable path → `blocked` with reason, not a silent skip.

## Adapters

| `outcomeKind` | Status | Meaning |
|---------------|--------|---------|
| `draft-pr` | **Live** (default for code) | Open a **draft** PR to `baseBranch` (respect `draftPrs`). Append `{ url, itemId, branch, draft }` to state `prs`. Counts toward `maxPrs`. |
| `doc-artifact` | **Live** (for `docs-digest`, `ops-checklist`) | Write or update a durable in-repo doc/path; **no PR** unless Sources override to `draft-pr`. Record path in item `notes`. |
| `branch-only` | **Live** | Push / leave an `after-hours/…` branch with commits; **no** PR. Record branch in item `notes` (+ cloud ledger when enabled). |
| `report-only` | **Live** | Findings only in morning brief / chat; no git publish unless the human asks. |
| `external-ticket-update` | **Live** (MVP) | Comment on the origin tracker (`gh issue comment` or known issue URL); no PR required. Record comment URL/id in `notes`. |

### `draft-pr` (today)

Default for `pr-slice` and `feature-build`. Typical for `research-only` when shipping research markdown via PR.

**If state `megaPr: true`** (dual-token arm only — [mega-pr.md](./mega-pr.md)):

1. Use one shared branch `after-hours/mega-<date>` for the whole run.
2. Open **at most one** draft PR for the run; fold later items via commits + PR body checklist.
3. `maxPrs` caps **items bundled**, not separate PR count (`prs.length` is `0` or `1`).
4. Still confirm draft; still denylist / no force-push.

**Else (default sliced):**

1. Branch from `baseBranch` if not already on an after-hours branch.
2. Commit executor output; push remote branch.
3. `gh pr create` with `--draft` when `draftPrs: true` (default).
4. Confirm draft when required; append to `prs`.
5. Idempotency: skip opening a second PR if an open draft already covers the item id.

Safety / denylist / no-force-push rules in [guardrails.md](./guardrails.md) still apply before publish.

### `doc-artifact` (live for `docs-digest` / `ops-checklist`)

Default for [`docs-digest`](../executors/docs-digest.md). Also used by [`ops-checklist`](../executors/ops-checklist.md) when Sources ask for a durable file (ops default is `report-only`).

1. Ensure the digest/file exists at the path resolved by the executor (acceptance path, `docs/after-hours/<id>-digest.md`, or ops `…-ops.md`).
2. Prefer committing on the current after-hours branch **only if** the project already expects overnight commits without a PR; otherwise leave the file in the working tree and record the path — do not invent a PR “to be safe.”
3. Set item `notes` to include the artifact path (e.g. `doc-artifact: docs/after-hours/github-52-digest.md`).
4. Do **not** append to `prs`; does **not** count toward `maxPrs`.
5. If Sources set `outcomeKind: draft-pr` instead, publish the same file via `draft-pr` after it exists.

Safety checklist before any commit/push: no secrets in the file; denylist check ([guardrails.md](./guardrails.md)).

### `branch-only` (live)

Push commits on an `after-hours/…` branch; **do not** open a PR. Prefer when review will happen on the branch, or when Sources intentionally skip PR noise.

1. Branch from `baseBranch` if not already on an after-hours branch (`after-hours/<slug>`).
2. Commit executor output; push the remote branch (`git push -u origin HEAD` — never `--force`; never push to `main`/`master` as the feature branch).
3. Do **not** run `gh pr create`. Do **not** append to `prs`. Does **not** count toward `maxPrs`.
4. Set item `notes` to include the branch (e.g. `branch-only: after-hours/fix-widget-slug`).
5. When `cloudLedgerPath` is set, upsert the ledger entry with `status: done` and the branch in the entry (see [cloud-ledger.md](./cloud-ledger.md)); no `prUrl`.
6. **Mega-PR:** `branch-only` stays branch-only — do **not** fold into the mega draft PR or invent a PR “because mega is on.” Mega dual-token rules still apply only to `draft-pr` bundling ([mega-pr.md](./mega-pr.md)).

Safety checklist: denylist / no secrets / no force-push ([guardrails.md](./guardrails.md)) before commit/push.

### `report-only` (live)

Findings only — morning brief and optional chat. **No** commit, push, or PR unless the human explicitly asks mid-run.

1. Complete the executor’s acceptance work in working memory / chat (and ephemeral notes as needed).
2. Do **not** publish via git (no commit/push/PR). Do **not** append to `prs`. Does **not** count toward `maxPrs`.
3. Set item `notes` to a short findings pointer (e.g. `report-only: <one-line summary>; see morning brief`).
4. On stop, include the findings under the morning brief **Doc / non-PR outcomes** / **Done** sections ([morning-brief.md](./morning-brief.md)); optionally paste the same summary in chat.
5. When `cloudLedgerPath` is set, upsert `status: done` with a short `notes`/`artifact` string (no `prUrl`) so Automation idempotency can skip re-work.

If acceptance actually requires a durable file or PR, Sources should set `doc-artifact` / `draft-pr` / `branch-only` instead — do not silently upgrade.

### `external-ticket-update` (live MVP)

Comment (or equivalent status update) on the origin tracker; **no** PR required.

1. Resolve the tracker target from item `ref` / Notes (GitHub issue URL or number preferred).
2. Prefer `gh issue comment <N> --body "…"` when `gh` + a GitHub issue are available. If an issue/ticket URL is known for another tracker and a CLI exists, post an equivalent comment; otherwise `blocked` with reason (do not invent a PR).
3. Do **not** append to `prs` unless Sources also requested `draft-pr` (unusual). Does **not** count toward `maxPrs`.
4. Set item `notes` to include the comment locator (e.g. `external-ticket-update: https://github.com/owner/repo/issues/52#issuecomment-…` or `comment-id: 1234567890`).
5. When `cloudLedgerPath` is set, upsert with `status: done` and the comment URL/id as `artifact` (no `prUrl` unless a PR also exists).

Keep comment bodies free of secrets; link to durable docs when the writeup is long ([guardrails.md](./guardrails.md)).

## Defaults by executor

| Executor | Default `outcomeKind` |
|----------|----------------------|
| `pr-slice` | `draft-pr` |
| `feature-build` | `draft-pr` |
| `research-only` | `draft-pr` (research markdown PR); may set `external-ticket-update` when a comment is the intentional publish |
| `docs-digest` | `doc-artifact` (no PR unless Sources override) |
| `ops-checklist` | `report-only` (no PR; `doc-artifact` when Sources ask for a durable file) |

Override per item via Sources / queue materialization when non-default outcomes are intended (examples in [bootstrap.md](./bootstrap.md) / [Sources.example.txt](../templates/Sources.example.txt)). Defaults stay `draft-pr` / `doc-artifact` / `report-only` (`ops-checklist`) unless overridden.

## Orchestration note

**Sources** remain the only night-time binding to a workflow. Outcome adapters extend *how work ships*; they do not fork the tick loop. See [composition.md](../docs/composition.md).
