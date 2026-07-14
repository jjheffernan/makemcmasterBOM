---
name: after-hours
description: >
  ALPHA — AFK overnight / late-session loop (not a release). Pluggable work
  sources (GitHub issues, TODO.md, feature specs, opt-in wayfinder-afk /
  github-tickets) and executors (incl. docs-digest, ops-checklist) →
  outcome adapters (draft-pr default for code; doc-artifact for digests;
  report-only for ops-checklist). Trigger when the
  user runs /after-hours, /after-hours-loop, /loop with after-hours
  instructions, a Cursor Automation (e.g. cron after office hours), or asks
  to drain ready-for-agent / AFK / overnight work while unattended.
disable-model-invocation: true
license: MIT
---

# after-hours (orchestrator) — **alpha**

**Status:** `0.1.0-alpha` — collect real runs before a release tag. After dogfood nights, score with the heff-skills repo scorecard (`docs/first-night-scorecard.md`).

Bootstrap **sources** → **work items** → **executors** → **outcome adapters** (default `draft-pr` for code; `doc-artifact` for `docs-digest`; `report-only` for `ops-checklist`) on `baseBranch`.

**A→Z** means executor-defined completion for the item plus its outcome adapter — not solely “opened a PR” ([outcomes](./references/outcomes.md), [glossary](./docs/glossary.md)).

**Sources are the only night-time binding** to a workflow — one orchestrator path; add source/outcome adapters, don’t fork the loop. Trackers are inputs ([composition](./docs/composition.md)).

## Load map

| Doc | When |
|-----|------|
| [references/bootstrap.md](./references/bootstrap.md) | Preflight, dry-run, Sources |
| [references/readiness.md](./references/readiness.md) | Before execute / claim |
| [references/compatibility.md](./references/compatibility.md) | Peer / Matt soft-detect (opt-in) |
| [references/guardrails.md](./references/guardrails.md) | Skip / block / stop / escalate |
| [references/state-schema.md](./references/state-schema.md) | state.json, queue contract, resume |
| [references/outcomes.md](./references/outcomes.md) | Outcome adapters (`draft-pr`, `doc-artifact`, `branch-only`, `report-only`, `external-ticket-update`) |
| [references/morning-brief.md](./references/morning-brief.md) | Every stop |
| [references/tick-and-runners.md](./references/tick-and-runners.md) | Sentinel, tick loop, Automation |
| [references/cloud-ledger.md](./references/cloud-ledger.md) | Optional durable Automation ledger (`cloudLedgerPath`) |
| [references/run-artifacts.md](./references/run-artifacts.md) | Optional per-tick verification evidence (`runsPath`) |
| [references/mega-pr.md](./references/mega-pr.md) | Bundled mega-PR — **explicit every run** (unsafe) |
| [docs/glossary.md](./docs/glossary.md) | Terms |
| [docs/composition.md](./docs/composition.md) | Orchestrator position; trackers as inputs |

Config: `.cursor/after-hours-loop.config.json` ← [templates/config.example.json](./templates/config.example.json).

## Invocation

| Trigger | Behavior |
|---------|----------|
| **`/after-hours`** | Primary. `/after-hours 45m`, `/after-hours --dry-run`, `/after-hours doctor`. Mega-PR only with `--mega-pr` **and** confirm line — [mega-pr](./references/mega-pr.md). |
| **`/loop`** + this skill | Equivalent when pointed here. |
| **Cursor Automation** | Cron (e.g. office hours close); same Sources in Instructions. See skill [tick-and-runners](./references/tick-and-runners.md) + install-tree / heff-skills [docs/automation.md](https://github.com/jjheffernan/heff-skills/blob/main/docs/automation.md). |

Flow: load skill → **preflight** → bootstrap → tick 0 (unless dry-run) → arm sentinel ([tick-and-runners](./references/tick-and-runners.md)).

Stop: `stop loop`, `stop after-hours`, `/after-hours stop`.

## Modules

| Layer | Path |
|-------|------|
| Sources | `sources/github-issues.md`, `todo-md.md`, `feature-spec.md`, `wayfinder-afk.md` (opt-in), `github-tickets.md` (opt-in) |
| Executors | `executors/pr-slice.md`, `feature-build.md`, `research-only.md`, `docs-digest.md`, `ops-checklist.md` |
| Outcomes | [references/outcomes.md](./references/outcomes.md) — adapters after completion |

Load only the active module. Do not paste their logic here.

## Defaults

| Key | Default |
|-----|---------|
| `repo` | `gh` cwd default |
| `baseBranch` | `main` |
| `draftPrs` | `true` |
| `maxPrs` | bootstrap or `3` |
| `maxConsecutiveBlocked` | `3` |
| `babysitCi` | `false` |
| `stopOnCiRed` | `false` |
| `allowEmptyQueue` | `false` |
| `statePath` | `.cursor/after-hours-loop.state.json` |
| `morningBriefPath` | `.cursor/after-hours-morning-brief.md` |
| `cloudLedgerPath` | `null` (off — PR idempotency only; see [cloud-ledger](./references/cloud-ledger.md)) |
| `runsPath` | `null` (off — see [run-artifacts](./references/run-artifacts.md)) |

## Bootstrap → tick

1. Follow [bootstrap.md](./references/bootstrap.md) (preflight fail-closed).
2. Materialize Sources ([templates/Sources.example.txt](./templates/Sources.example.txt)); priority `github-first` default.
3. Apply [readiness](./references/readiness.md).
4. **Dry-run:** print queue; no state write; no code; stop. **Doctor:** env + readiness scan only ([bootstrap](./references/bootstrap.md)).
5. Else write state ([state-schema](./references/state-schema.md)); run tick 0; continue per [tick-and-runners](./references/tick-and-runners.md).
**Hard dep:** agent-ready work for the chosen Sources/executors, or stop with a morning note for daytime alignment.  
**Soft deps:** CONTEXT / ADRs / issue-tracker / Matt or other peer skills **if present** — [compatibility](./references/compatibility.md). Never rewrite CONTEXT/ADRs; never `/grill-me` or HITL wayfinder overnight.  
**Refuse:** never require grill→tickets (or any peer chain) to start — bootstrap from Sources alone ([first-night](https://github.com/jjheffernan/heff-skills/blob/main/docs/first-night.md), [smoke-matrix](https://github.com/jjheffernan/heff-skills/blob/main/docs/smoke-matrix.md)).

## Stop output

Every stop → [morning brief](./references/morning-brief.md) at `morningBriefPath` ([templates/morning-brief.md](./templates/morning-brief.md)).
