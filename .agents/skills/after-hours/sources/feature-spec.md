# Work source: `feature-spec`

Feature build-out from plan docs (PRD, wayfinder handoff, `docs/**/*-plan.md`, etc.).

## Bootstrap config

```text
feature-spec: docs/plans/example-plan.md
feature-spec: docs/plans/example-plan.md phase 1
feature-spec: path/to/plan.md slice "helper module"
```

| Field | Meaning |
|-------|---------|
| path | Repo-relative plan doc |
| phase / slice | Optional scope filter within doc |

## Materialize (hybrid)

Read plan doc. Then:

### A. Explicit vertical slices in doc

If plan lists named slices, phases with checklists, or vertical-slice sections → **pre-split** one work item per slice:

```json
{
  "id": "feature:example-helper",
  "title": "helper module",
  "source": "feature-spec",
  "executor": "feature-build",
  "ref": "docs/plans/example-plan.md",
  "acceptance": "slice acceptance from plan",
  "verification": ["<optional commands from plan verification block>"],
  "risk": "medium",
  "granularity": "single-pr",
  "status": "open",
  "sliceHint": "helper module"
}
```

If the plan names a **verification** / **test plan** command list for the slice, populate `verification`. Parse `risk:` when the plan states it.

### B. Phase-level only

If plan says "Phase 1" without slice breakdown → one **umbrella** item:

```json
{
  "id": "feature:example-phase1",
  "title": "Example Phase 1",
  "source": "feature-spec",
  "executor": "feature-build",
  "ref": "docs/plans/example-plan.md",
  "granularity": "multi-slice",
  "status": "open",
  "children": []
}
```

`feature-build` decomposes on first tick and appends child items to state queue. Children use IDs like `feature:example-phase1:1-helper`.

Parent → `done` only when all children `done` or `blocked`.

## Default executor

Always `feature-build` unless bootstrap override.

## Blocked

Mark `blocked` when plan requires:

- An unresolved human product decision
- Acceptance criteria that are missing or contradictory (see [readiness.md](../references/readiness.md))
- Scope explicitly out of the bootstrap filter

Do not invent slices beyond what the plan supports.

## Refresh

Static at bootstrap. Children appended at runtime by executor only.
