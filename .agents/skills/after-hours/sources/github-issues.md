# Work source: `github-issues`

PR-oriented issue tracking via `gh`.

## Bootstrap config

```text
github-issues: label ready-for-agent limit 5
github-issues: numbers 52,61,70
```

| Field | Default |
|-------|---------|
| `label` | `ready-for-agent` |
| `limit` | `10` |
| `numbers` | optional comma-separated issue numbers (ignores label query) |

## Repo resolution

1. `.cursor/after-hours-loop.config.json` → `repo` (`owner/name`) if set
2. Else `gh repo view --json nameWithOwner -q .nameWithOwner` for cwd
3. Never invent a hardcoded owner/repo

## Soft tracker ops

**If present:** soft-read `docs/agents/issue-tracker.md` for label names, triage flow, and comment conventions. Prefer those labels/ops over inventing a second dialect. **If absent:** use the bootstrap `label` (default `ready-for-agent`) and Agent Brief rules below.

## Materialize work items

```bash
# REPO from config or gh default
gh issue list --repo "$REPO" \
  --label ready-for-agent --state open \
  --json number,title,url,body,labels --limit 10
```

For explicit numbers: `gh issue view N --repo "$REPO" --json number,title,url,body,labels,comments`.

Fetch comments when materializing (or when body alone is insufficient):

```bash
gh api "repos/$REPO/issues/N/comments" --jq '.[].body'
```

### Agent Brief (preferred acceptance)

Find acceptance in this order:

1. **Issue comment** whose body is titled or contains **`Agent Brief`** (heading, bold line, or first-line label — e.g. `## Agent Brief`, `**Agent Brief**`, `Agent Brief:`).
2. Else an **`Agent Brief` section** in the issue body (same title/heading cues).
3. Else the first acceptance / criteria / “Done when” block in the body.
4. Else a short body excerpt.

**If an Agent Brief is present** → set work item `acceptance` to that brief’s content (full brief, or the acceptance/criteria portion if clearly subsectioned). Treat it as the AFK contract.

**Verification list:** if the Brief (or body) includes a `verification:` / “Verify with” / checklist of shell commands, materialize them as item `verification: string[]`. Prefer Brief commands over inventing new ones.

**Risk:** if Brief/labels say `risk: high|medium|low` (or equivalent), set item `risk`. Default omit → treat as `medium` at execute time.

**If labeled `ready-for-agent` (or tracker equivalent) but no Agent Brief and body is vague** → still **materialize** the work item (`status: open`) with best-effort `acceptance` excerpt. Do **not** invent scope. The [readiness gate](../references/readiness.md) marks the item **`blocked`** on tick rather than executing. Prefer unblocking in daytime (triage / brief / human alignment) over overnight guessing.

### Work item shape

Map each issue to:

```json
{
  "id": "github:52",
  "title": "<title>",
  "source": "github-issues",
  "executor": "pr-slice",
  "ref": "<url>",
  "acceptance": "<Agent Brief or body excerpt>",
  "granularity": "single-pr",
  "status": "open"
}
```

Default `executor: pr-slice`. Override at bootstrap if issue body references a plan doc → `feature-build`.

Optional metadata when useful: `hasAgentBrief: true|false`.

## Refresh

- **Cloud Automation:** re-query each tick; drop issues no longer open; do not re-add `done` IDs from current run's state.
- **In-session:** optional refresh at tick start; preserve in-flight item.

## Completion (executor callback)

After successful PR:

1. PR body includes `Fixes #N` or `Closes #N`.
2. Optional: `gh issue comment N --body "After-hours: <PR URL>"`.
3. Do **not** auto-close issue unless merge policy does — mark work item `done` when PR is opened.

## Blocked

Mark `blocked` without PR when issue:

- Needs a human product decision, or body/label indicates blocked / needs-info / ready-for-human
- Lacks actionable acceptance and no Agent Brief (readiness gate — still left in queue as `blocked`)
- Touches scope the user forbade in bootstrap
