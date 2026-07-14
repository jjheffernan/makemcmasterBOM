---
name: after-hours-stop
description: >
  Opt-in stop / teardown for after-hours-loop: kill the in-session sentinel,
  honor stop phrases, persist stopReason, and ensure a morning brief is written.
  Trigger when the user says stop after-hours, stop loop, /after-hours stop,
  or asks to halt an armed overnight run without starting a new loop.
disable-model-invocation: true
license: MIT
---

# after-hours-stop (companion)

Thin companion to **after-hours-loop**. Do **not** bootstrap a new overnight run — only stop and hand off.

## When to use

- User: `stop after-hours`, `stop loop`, `/after-hours stop`
- Explicit ask to kill the AFK sentinel / end the night

## Path notes

Canon lives in the after-hours-loop skill. Resolve references as:

| Layout | Base |
|--------|------|
| Repo SoT (sibling) | `../after-hours-loop/` |
| Installed project | `.agents/skills/after-hours-loop/` |

Follow those paths for detail; do not duplicate policies here.

## Stop procedure

1. **Kill sentinel** — Find the in-session `AGENT_LOOP_TICK_AFTERHOURS` / sleep loop; kill its PID; do **not** re-arm. Automation cron: do not schedule further ticks from this session (next fire is separate). See `references/tick-and-runners.md`.
2. **Persist stop** — Set coarse `stopReason` + optional `stopDetail` on state (`done` / `user-stop` for human stop). See `references/state-schema.md`, `references/guardrails.md`.
3. **Morning brief** — Write the brief on **every** stop path (including user-stop). See `references/morning-brief.md` and `templates/morning-brief.md`. Default path: config `morningBriefPath` or `.cursor/after-hours-morning-brief.md`.
4. Confirm in chat: sentinel dead (or N/A for Automation), brief path, stop reason.

## Out of scope

- Starting `/after-hours`, picking queue items, opening PRs
- Always-on hooks — this skill is **user-invoked only** (`disable-model-invocation: true`)
