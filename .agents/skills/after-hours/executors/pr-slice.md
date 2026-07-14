# Executor: `pr-slice`

One focused fix → one **draft** PR to the configured **base branch**.

## Config

From `.cursor/after-hours-loop.config.json` (defaults in brackets):

- `baseBranch` [`main`]
- `draftPrs` [`true`]
- `testCommand` [empty → infer]
- `packageManager` [`auto` → detect from lockfile / `package.json`]
- `safety.pathDenylist` — refuse and **stop loop** if changes would touch matched paths

## Branch

```bash
BASE="${baseBranch:-main}"
git fetch origin "$BASE"
git checkout "$BASE" && git pull --ff-only origin "$BASE"
git checkout -b after-hours/<slug>
```

Slug from work item title (kebab-case, max ~40 chars).

**Mega-PR:** if state `megaPr: true`, follow [mega-pr.md](../references/mega-pr.md) / [outcomes.md](../references/outcomes.md) shared branch instead — do **not** open a per-item PR.

## Implement

1. Soft-read **ponytail** (or similar minimal-diff skill) **if installed** — smallest working change. Else: change only what acceptance requires; **no drive-by files** (no opportunistic refactors, formatting sweeps, or unrelated cleanup).
2. Scope to item `acceptance` + `ref` only. If acceptance is vague → `blocked`.
3. Soft-read `CONTEXT.md` / ADRs if present; do not rewrite them.
4. Domain Task subagents: use only if the **project** documents them; otherwise stay in-process.

## Tests / verification

1. If item `verification` is a non-empty list → run **each** command in order; record exits (see [run-artifacts.md](../references/run-artifacts.md) when `runsPath` set).
2. Else if `testCommand` set → run it.
3. Else try package manager test script (`pnpm test` / `npm test` / `yarn test` / `bun test`) or project README’s documented command.
4. One fix attempt on failure; then mark item `blocked` (`verification-failed` or `tests`). **Never** drop or weaken verification to force `done`.
5. If no verification and no test command: set residual risk; mark `blocked` unless `allowSkipTests: true` **and** item had no `verification[]`.
6. Respect item `risk` ([readiness.md](../references/readiness.md)): high without `allowHighRisk: true` → skip, do not implement.

## PR

```bash
BASE="${baseBranch:-main}"
DRAFT_FLAG=""
# when draftPrs true (default):
DRAFT_FLAG="--draft"

gh pr create --base "$BASE" $DRAFT_FLAG \
  --title "fix(after-hours): <short title>" \
  --body "$(cat <<'EOF'
## Summary
- …

## Work item
- <id> — <ref>

## Test plan
- [ ] …
EOF
)"
```

For `github-issues` items: include `Fixes #N` in body. No auto-merge.

## Safety checklist

Before commit / push / `gh pr create`:

- [ ] Draft flag matches `config.draftPrs` (`--draft` when true).
- [ ] Denylist check on staged/changed paths vs `safety.pathDenylist` — any match → **stop loop** escalate; never open PR ([guardrails.md](../references/guardrails.md)).
- [ ] Auth / webhook / guard **weakening** → **stop loop** escalate (not merely block item).
- [ ] Never `--force` push; never push to `main`/`master` as the feature branch — push only `after-hours/…` and PR into `baseBranch`.
- [ ] Diff is self-contained: no drive-by files beyond acceptance (ponytail if present; else same minimal-diff rule).

## TODO write-back

If item `source` is `todo-md`, follow [todo-md.md](../sources/todo-md.md) auto check-off in same branch before push.

## Outcome

Executor emits a **completion signal**; publish via [outcome adapter](../references/outcomes.md) (`outcomeKind`, default **`draft-pr`**). Do not treat “opened a PR” as the only definition of done — that is today’s default adapter for this executor. Choose **`branch-only`** when Sources want commits without a PR; **`report-only`** when findings should stay in the morning brief only.

| Result | Item status |
|--------|-------------|
| Adapter succeeds + tests pass (or skip allowed) | `done` |
| Cannot scope / blocked guardrail / adapter fail | `blocked` |
| User skip | `skipped` |

For `draft-pr`: append `{ "url": "...", "itemId": "...", "branch": "after-hours/...", "draft": true }` to state `prs`.

**After open:** if `draftPrs: true`, confirm draft with `gh pr view <url> --json isDraft -q .isDraft` (must be `true`). If not draft → convert to draft or **stop loop** (`stopReason: blocked`, `stopDetail: guardrail`) — never leave an overnight PR merge-ready by mistake.
