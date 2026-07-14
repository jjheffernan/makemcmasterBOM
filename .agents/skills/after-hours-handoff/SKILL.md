---
name: after-hours-handoff
description: >
  Opt-in morning-brief handoff after an after-hours stop. Refresh or rewrite
  the durable morning brief from current state (PRs, blocked, residual risk,
  suggested next). Trigger when the user asks for a morning brief, handoff,
  or post-stop summary without starting a new overnight loop.
disable-model-invocation: true
license: MIT
---

# after-hours-handoff (companion)

Thin companion to **after-hours-loop**. Focus: durable **morning brief** after a stop (or when the human asks for handoff without arming a new run).

## When to use

- After `stop after-hours` / `/after-hours stop` when the brief needs a refresh
- User asks for morning brief / overnight handoff / “what happened last night”
- Prefer this over starting `/after-hours` solely to summarize

## Path notes

Canon lives in the after-hours-loop skill. Resolve references as:

| Layout | Base |
|--------|------|
| Repo SoT (sibling) | `../after-hours-loop/` |
| Installed project | `.agents/skills/after-hours-loop/` |

Primary docs: `references/morning-brief.md`, `templates/morning-brief.md`. State shape: `references/state-schema.md`.

## Handoff procedure

1. **Locate state** — Config `statePath` (default `.cursor/after-hours-loop.state.json`). If missing, note gap in the brief; do not invent PRs or queue outcomes.
2. **Write brief** — Path from `morningBriefPath` or `.cursor/after-hours-morning-brief.md`. Follow the morning-brief template (Summary, PRs, doc artifacts, Done / Blocked / Skipped, residual risk, suggested next).
3. **Stop line** — Include `stopReason` / `stopDetail` when present on state.
4. **Chat pointer** — Tell the human the brief path; keep chat short (pointers > dumps).

## Out of scope

- Killing the sentinel (use **after-hours-stop**) or starting a new loop
- Always-on hooks — this skill is **user-invoked only** (`disable-model-invocation: true`)
