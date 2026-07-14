# Executor: `feature-build`

Build from plan doc → one **draft** PR per **slice** to the configured **base branch**.

## Config

Same keys as [pr-slice.md](./pr-slice.md): `baseBranch`, `draftPrs`, `testCommand`, `packageManager`, safety denylist.

## Soft skill chain

**If installed** in `.agents/skills` or `.cursor/skills`: prefer `implement` → `tdd` → `code-review` (or project equivalents).  
**Else:** implement acceptance with tests at seams you touch; self-review the diff before opening the PR.

Soft-read `CONTEXT.md` / `docs/adr/*` if present — never rewrite overnight.

## Branch

```bash
BASE="${baseBranch:-main}"
git fetch origin "$BASE"
git checkout "$BASE" && git pull --ff-only origin "$BASE"
git checkout -b after-hours/feature-<slug>
```

Slug from work item id or `sliceHint`.

## Umbrella decomposition (first tick only)

If item `granularity` is `multi-slice` and queue has no children yet:

1. Read plan at `ref`.
2. Propose 2–5 vertical slices (each normally one PR); do not invent product decisions.
3. Append child work items to state `queue` (inherit `source: feature-spec`, `executor: feature-build`, `granularity: single-pr`, `parentId: <umbrella id>`).
4. Do **not** mark umbrella `done` — process first child on same or next tick.

**Mega-PR:** children still decompose for work scoping, but all publish onto the **one** mega draft PR ([mega-pr.md](../references/mega-pr.md)) — do not open 2–5 PRs.

## Implement slice

1. Read plan doc + item `acceptance` / `sliceHint`.
2. Implement + targeted tests; typecheck if the project has it. Soft-read **ponytail** if installed; else **no drive-by files** beyond the slice.
3. Review diff before PR (skill if present, else manual checklist).

## Escalate (mark `blocked`, do not hack)

| Scope | Action |
|-------|--------|
| Schema / data migration with unclear rollback | `blocked` |
| Auth / permission / webhook guard weakening | **Stop loop** escalate (not just block) |
| Large opportunistic refactor / drive-by files | `blocked` — out of after-hours slice |
| Missing acceptance | `blocked` |

## Tests

Same rules as [pr-slice.md](./pr-slice.md) **Tests / verification** (item `verification[]` first; never green-wash; honor `risk`).

## PR

**If `megaPr: true`:** append commits to the shared mega branch / update the single draft PR body (checklist of item ids). Skip per-slice `gh pr create`.

**Else (default):**

```bash
BASE="${baseBranch:-main}"
DRAFT_FLAG="--draft"   # unless draftPrs false

gh pr create --base "$BASE" $DRAFT_FLAG \
  --title "feat(after-hours): <slice title>" \
  --body "$(cat <<'EOF'
## Summary
- …

## Plan
- <ref>
- Slice: <sliceHint>

## Test plan
- [ ] …
EOF
)"
```

Link GitHub issue in body if parent originated from `github-issues`.
## Safety checklist

Before commit / push / `gh pr create`:

- [ ] Draft flag matches `config.draftPrs` (`--draft` when true).
- [ ] Denylist check on staged/changed paths vs `safety.pathDenylist` — any match → **stop loop** escalate; never open PR ([guardrails.md](../references/guardrails.md)).
- [ ] Auth / webhook / guard **weakening** → **stop loop** escalate (not merely block item).
- [ ] Never `--force` push; never push to `main`/`master` as the feature branch — push only `after-hours/…` and PR into `baseBranch`.
- [ ] Diff is self-contained: no drive-by files beyond the slice (ponytail if present; else same minimal-diff rule).

## TODO write-back

If item or parent linked `todo-md`, run check-off per [todo-md.md](../sources/todo-md.md).

## Outcome

Completion signal + [outcome adapter](../references/outcomes.md) (`outcomeKind`, default **`draft-pr`**). A→Z means executor-defined completion for the slice, then the requested adapter — not “must open a PR” in the abstract. Prefer **`branch-only`** for slice commits without opening a PR; **`report-only`** only when the slice is intentionally findings-only (unusual for this executor).

| Result | Item status |
|--------|-------------|
| Adapter succeeds for slice | child `done`; umbrella `done` when all children terminal |
| Cannot decompose umbrella | umbrella `blocked` |
| Tests fail after one fix / adapter fail | slice `blocked` |

For `draft-pr`: append `{ "url", "itemId", "branch", "draft" }` to state `prs` when a PR was opened.

**After open:** if `draftPrs: true`, confirm `gh pr view <url> --json isDraft -q .isDraft` is `true`; else convert to draft or **stop loop**.
