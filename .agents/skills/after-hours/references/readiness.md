# Agent-ready checklist

Before executing an item, decide: **agent-ready** or not. Overnight must not invent product scope.

Trackers and peer pipelines are **inputs** that may supply evidence for these gates — they are not a required chain before AFK can start. What enters the queue is decided by **Sources**.

## Agent-ready (ANY one is enough)

| Gate | How to detect |
|------|----------------|
| **(a) Label** | Issue (or tracker row) has `ready-for-agent` (or config-equivalent label). |
| **(b) Agent Brief** | Issue comment or attached brief titled/marked **Agent Brief** with do / don't / acceptance. Prefer Brief over raw body. |
| **(c) Explicit acceptance** | TODO checkbox, feature-spec section, or item `acceptance` lists testable criteria. |
| **(d) Frontier ticket** | Item comes from a frontier / deps tracker (opt-in **`github-tickets`** source when present) **and** open blockers on that ticket are closed. |

If none apply → do **not** execute.

## Not ready → `blocked`

| Field | Value |
|-------|--------|
| `status` | `blocked` |
| `blockReason` | `needs-info` or `needs-grill` (see also portable `blockerPolicy` in [state-schema.md](./state-schema.md)) |

- **`needs-info`** — missing acceptance, unclear files/API, env/secret unknown, conflict with CONTEXT/ADRs.
- **`needs-grill`** — alignment unfinished; product choices still open; brief is foggy. Name is historical — means “needs daytime human alignment,” not “must run `/grill-me`.”

Record reason on the item and in the morning brief. **Never invent requirements overnight.**

## HITL-shaped work — skip / block

Treat as not AFK-safe (mark `blocked` or `skipped`; do not start product work / outcome adapters that ship features):

- Explicit product / design decision for a human
- Design-only or exploratory UI without acceptance
- Ambiguous one-liner brief with no criteria
- Wayfinder grilling / prototype HITL tickets (see [compatibility.md](./compatibility.md))
- Labels like `ready-for-human`, `needs-info`, `blocked` (unless the human already resolved them and left agent-ready evidence)

## Claim semantics

1. Before coding (or other execute work), set the item `status` to **`in-progress`** in state JSON (`statePath`).
2. Persist claim before branch creation, file edits, or other side effects.
3. One claimed item at a time per loop run (unless umbrella parent with children — parent stays `open`; only the active child is `in-progress`).
4. On stop mid-item: leave `in-progress` (resume next tick) or demote to `open` if you cannot safely continue — note residual risk in the morning brief.

See [state-schema.md](./state-schema.md).

## Verification contract

Before marking an item `done`:

1. Prefer item `verification: string[]` when present (from Agent Brief / feature-spec / Sources).
2. Else, if the executor requires tests, run config `testCommand` (or project-inferred suite).
3. If a verification command fails after one honest fix attempt → **`blocked`** with `blockReason: verification-failed` (or `tests`). Do **not** delete criteria, skip commands, or soften acceptance to force `done`.
4. `allowSkipTests: true` only skips when **no** item `verification[]` was listed **and** config allows skipping the shared `testCommand` — never skip an explicit per-item verification list.

## Risk

| `risk` | Overnight behavior |
|--------|-------------------|
| `low` | Normal execute |
| `medium` (default) | Normal execute |
| `high` | Prefer **skip** or **block** unless Sources/bootstrap explicitly allow high-risk AFK (`allowHighRisk: true` in kickoff). When allowed: still full verification; prefer smaller slice / lower budget for that item |

Never invent `risk: low` to dodge caution.