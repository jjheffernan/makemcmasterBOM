# after-hours / after-hours-loop

**Status: alpha (`0.1.0-alpha`)** — dogfood before release.

AFK overnight loop for Cursor: pluggable **work sources** + **executors** → **outcome adapters** (`draft-pr` default for code). Trackers are inputs; **Sources** are the only night-time binding. Works from `/after-hours`, `/loop`, or **Cursor Automation** when office hours close.

Part of [heff-skills](https://github.com/jjheffernan/heff-skills).

## Triggers

| Command | Role |
|---------|------|
| `/after-hours` | Primary — bootstrap, tick 0, arm sentinel |
| `/after-hours --dry-run` | Queue only; no state / coding |
| `/after-hours doctor` | Env + readiness scan; no arm |
| `/after-hours 30m` | Same with custom interval |
| `/loop …` + this skill | Equivalent when pointed here |
| Cursor Automation | Unattended cron (office-hours close) — [docs/automation.md](https://github.com/jjheffernan/heff-skills/blob/main/docs/automation.md) · [instructions template](./templates/automation-instructions.office-hours.close.txt) |
| Mega-PR (unsafe) | Dual-token only — [mega-pr.md](./references/mega-pr.md); never config-sticky |

Stop: `stop after-hours` / `stop loop`.## Install

Primary (when published / registry-available):

```bash
npx skills add jjheffernan/heff-skills -a cursor
```

Alternative from a heff-skills clone:

```bash
./scripts/install.sh /path/to/your/project --with-gitignore
```

Or see [INSTALL.md](https://github.com/jjheffernan/heff-skills/blob/main/INSTALL.md). Then copy and edit:

```bash
cp skills/after-hours-loop/templates/config.example.json \
  /path/to/your/project/.cursor/after-hours-loop.config.json
```

## Kickoff

```text
/after-hours 45m
Sources:
  - github-issues: label ready-for-agent limit 5
  - todo-md: section "Now"
maxPrs: 3
priority: github-first
```

Dry-run (queue only, no coding):

```text
/after-hours --dry-run
Sources:
  - github-issues: label ready-for-agent limit 5
```

## Optional Cursor rule

Not always-on overnight. To help the agent find the skill when you type `/after-hours`, optionally copy:

```bash
cp skills/after-hours-loop/templates/cursor-rule.after-hours-loop.mdc.example \
  /path/to/your/project/.cursor/rules/after-hours-loop.mdc
```

Keep `alwaysApply: false` — the rule is a thin pointer at `.agents/skills/after-hours-loop/SKILL.md`, not an armed overnight loop.

## Layout (source of truth)

| Path | Use |
|------|-----|
| `SKILL.md` | Thin orchestrator |
| `references/` | Bootstrap, readiness, compatibility, guardrails, state, outcomes, morning brief |
| `sources/` | Work source modules (incl. opt-in `wayfinder-afk`, `github-tickets`) |
| `executors/` | `pr-slice`, `feature-build`, `research-only`, `docs-digest`, `ops-checklist` (completion → outcome adapter) |
| `templates/` | Config, Sources, night presets, Automation Instructions, morning-brief, drop-in pointer, optional Cursor rule, gitignore snippet |
| `fixtures/` | Sample state JSON for `validate-state.py` |

Generated install tree: repo-root `drop-in/` (`./scripts/sync-drop-in.sh`).

## Optional peers

- [ponytail](https://github.com/DietrichGebert/ponytail) — minimal-diff discipline (soft)
- [mattpocock/skills](https://github.com/mattpocock/skills) — optional peer **inputs** (wayfinder / tickets / briefs); soft-compat only; never required to start AFK

Not bundled. Loop degrades cleanly without them.

## Not included

- Target-repo `TODO.md` / domain subagents
- Live session state (gitignored under `.cursor/`)

Parse / priority / write-back harnesses beyond the state fixtures in [`fixtures/`](./fixtures/) (see that README for `validate-state.py`).

## Uninstall / residual state

1. Stop any armed sentinel (`stop after-hours` / kill matching loop PID).
2. Remove the skill: `rm -rf .agents/skills/after-hours-loop`
3. Optionally delete session artifacts: `.cursor/after-hours-loop.state.json`, `.cursor/after-hours-morning-brief.md`, and config if unused.
4. Drop gitignore lines added solely for those files.

Full matrix: [INSTALL.md](https://github.com/jjheffernan/heff-skills/blob/main/INSTALL.md).
