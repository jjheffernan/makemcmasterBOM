# Work source: `wayfinder-afk`

Opt-in AFK slice of [wayfinder](https://github.com/mattpocock/skills) map tickets. **Never** runs grilling or prototype HITL overnight.

## Activation (hard)

Activate **only** when the bootstrap **Sources** line includes `wayfinder-afk: …`.

| Situation | Build behavior |
|-----------|----------------|
| Sources include `wayfinder-afk: …` | Discover map + enqueue AFK-safe children (below) |
| Open `wayfinder:map` exists but Sources **omit** `wayfinder-afk` | **Ignore for build** — do not enqueue map children. Morning brief **may** note that a map issue exists |
| No map issue | No-op for this source |

## Bootstrap config

```text
wayfinder-afk: label wayfinder:map
wayfinder-afk: map 88
wayfinder-afk: map 88 include-task
wayfinder-afk: label wayfinder:map limit 5
```

| Field | Meaning | Default |
|-------|---------|---------|
| `label` | Label on the **map** issue to discover | `wayfinder:map` |
| `map` | Explicit map issue number (skips label discovery) | — |
| `include-task` | Also enqueue `wayfinder:task` children marked AFK | off — research only unless set |
| `limit` | Max child items to enqueue | `5` |

Repo resolution: same as [github-issues.md](./github-issues.md) (config `repo`, else `gh` default). Soft-read `docs/agents/issue-tracker.md` if present for label spelling.

## Discover map

1. If `map N` given → `gh issue view N …`.
2. Else list open issues with label `wayfinder:map` (or bootstrap `label`). Prefer a single open map; if several, take the newest unless bootstrap specifies `map`.

Do not invent map IDs or owner/repos.

## Enqueue children (allowlist)

From the map issue body, linked issues, and/or GitHub sub-issues / tracked issues:

| Label | Enqueue? |
|-------|----------|
| `wayfinder:research` | **Yes** (primary AFK type) |
| `wayfinder:task` | **Only if** Notes / issue body / bootstrap mark it **AFK** (e.g. `AFK`, `after-hours`, `safe for overnight`) **or** Sources includes `include-task` |
| `wayfinder:grilling` | **Never** |
| `wayfinder:prototype` | **Never** |

Skip closed children. Cap at `limit`.

## Executor routing

For each enqueued child:

1. If `executors/research-only.md` exists → `executor: research-only`.
2. Else → materialize as `status: blocked`, `blockReason: missing-research-only` — **do not** fall back to `pr-slice` overnight (avoids accidental product diffs).

Never route grilling/prototype tickets through any executor.

## Work item shape

```json
{
  "id": "wayfinder:91",
  "title": "<child title>",
  "source": "wayfinder-afk",
  "executor": "research-only",
  "ref": "<child issue url>",
  "acceptance": "<research scope from brief/Notes; writeup only>",
  "granularity": "single-pr",
  "status": "open",
  "parentId": "wayfinder-map:88"
}
```

Map parent is **not** a build item (unless separately queued elsewhere). Optional: record map id in state for morning brief.

## Refresh

Same spirit as `github-issues`: re-query on Automation ticks; do not re-add `done` IDs; never pull in grilling/prototype mid-run.

## Morning brief

If a `wayfinder:map` was seen but this source was inactive, morning brief may say: map open, not drained (add `wayfinder-afk` to Sources to research overnight).

## Blocked

Mark `blocked` when the child lacks AFK-safe acceptance, needs human product/HITL input, or is mislabeled grilling/prototype after enqueue (drop / block — do not implement).
