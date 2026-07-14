# Work source: `github-tickets`

Opt-in consumer of [to-tickets](https://github.com/mattpocock/skills) **frontier** work — tracer-bullet implementation tickets whose blockers are closed. Complements labeled [github-issues](./github-issues.md); this source prefers deps / local scratch tickets over a flat label list.

## Activation (hard)

Activate **only** when the bootstrap **Sources** line includes `github-tickets: …`.

| Situation | Build behavior |
|-----------|----------------|
| Sources include `github-tickets: …` | Discover frontier tickets (GitHub and/or local scratch) and enqueue unblocked ready items |
| Open to-tickets / `.scratch/*/issues` exist but Sources **omit** `github-tickets` | **Ignore for build** — do not invent or drain tickets. Morning brief **may** note local scratch exists |
| No frontier candidates | No-op for this source |

**Never invent tickets overnight.** Only enqueue artifacts already published by daytime `/to-tickets` (or equivalent) that already look like implementation tickets.

## Bootstrap config

```text
github-tickets: label ready-for-agent limit 5
github-tickets: frontier limit 5
github-tickets: local .scratch limit 5
github-tickets: label ready-for-agent local .scratch limit 5
```

| Field | Meaning | Default |
|-------|---------|---------|
| `label` | Triage label on GitHub issues to consider | `ready-for-agent` (or tracker equivalent) |
| `frontier` | Prefer deps-based frontier discovery (blocked-by / sub-issues) | implied when GitHub path active |
| `local` | Also/only read `.scratch/*/issues/*.md` when present | off unless `local` set (path default `.scratch`) |
| `limit` | Max items to enqueue from this source | `5` |

Repo resolution: same as [github-issues.md](./github-issues.md) (config `repo`, else `gh` default).

## Soft tracker ops

**If present:** soft-read `docs/agents/issue-tracker.md` for label names, claim/comment conventions, and how blocking edges are represented. Prefer those ops over inventing a second dialect.

**If absent:** use bootstrap `label` (default `ready-for-agent`) and the frontier / Agent Brief rules below.

## Discover frontier (unblocked only)

Work the **frontier**: open tickets that look like implementation slices **and** have no open blockers.

### GitHub (when `gh` + repo available)

1. List open issues with `ready-for-agent` (or tracker label from issue-tracker / bootstrap).
2. Prefer issues that look like implementation tickets (Agent Brief, acceptance checklists, “Blocked by”, linked plan/spec) over triage/meta/discussion-only issues.
3. For each candidate, resolve **blockers** via (in order):
   - Native GitHub blocking / sub-issue / tracked-by relationships when `gh` exposes them
   - Else “Blocked by” / dependency lines in body or Agent Brief
   - Else soft-read issue-tracker conventions
4. **Enqueue only if every blocker is closed** (or explicitly “None — can start immediately”).
5. Cap at `limit`. Skip closed issues. Do not invent missing blockers or tickets.

### Local scratch (when `local` set **or** `.scratch/*/issues/*.md` present and Sources asked for local)

1. Glob `.scratch/*/issues/*.md` (or bootstrap path under `local`).
2. Parse each file for Status / Blocked-by / acceptance (mattpocock-style per-ticket files).
3. Enqueue only files whose status is agent-ready (e.g. `ready-for-agent`) **and** whose listed blockers are done (referenced sibling file closed/done, or “None”).
4. Cap at `limit`. Never create new `.scratch` tickets overnight.

If both GitHub and local yield candidates, merge and respect `limit` (prefer GitHub unless bootstrap is `local`-only).

## Agent Brief + readiness

Soft-read **Agent Brief** the same way as [github-issues.md](./github-issues.md) (comment titled Agent Brief → body section → acceptance excerpt).

Then apply the [readiness](../references/readiness.md) gate — especially **(d) Frontier ticket**. Vague / blocked / HITL → materialize as `blocked` or skip; **do not** invent scope.

## Executor routing

| Signal | Executor |
|--------|----------|
| Default | `pr-slice` |
| Body / Brief / local file links a plan or multi-phase feature-spec | `feature-build` |

Never invent a third executor overnight. Research-only / wayfinder HITL work belongs to other sources.

## Work item shape

```json
{
  "id": "ticket:52",
  "title": "<title>",
  "source": "github-tickets",
  "executor": "pr-slice",
  "ref": "<issue url or .scratch path>",
  "acceptance": "<Agent Brief or ticket acceptance>",
  "granularity": "single-pr",
  "status": "open"
}
```

Local scratch ids: `ticket:scratch:<feature>/<NN>-<slug>`. Optional: `hasAgentBrief`, `blockers: []` when useful for the morning brief.

## Refresh

Re-query frontier each Automation tick (and optionally at in-session tick start). Drop items whose blockers re-opened or that left `ready-for-agent`. Do not re-add `done` IDs. Never publish new tickets mid-run.

## Completion (executor callback)

Same spirit as `github-issues`: PR body `Fixes #N` / `Closes #N` when GitHub; optional comment with PR URL. For local scratch: mark the ticket file status done / note PR in morning brief — do not invent tracker rows.

## Blocked

Mark `blocked` (do not PR) when:

- Any listed blocker is still open
- Lacks actionable acceptance and no Agent Brief (readiness)
- Needs a human product decision / `ready-for-human` / needs-info
- Is triage/meta, not an implementation ticket
- Touches scope the user forbade in bootstrap
