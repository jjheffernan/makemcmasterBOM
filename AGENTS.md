# AGENTS.md

Guidance for coding agents working in this repo.

## Read first

| Doc | Why |
|-----|-----|
| [docs/development.md](docs/development.md) | Dev loop, scripts, pytest |
| [docs/architecture.md](docs/architecture.md) | System layout |
| [docs/testing.md](docs/testing.md) | Test expectations |
| [docs/plans/engineer-density-v1.md](docs/plans/engineer-density-v1.md) | Current after-hours feature slices |
| [TODO.md](TODO.md) | Agent-ready overnight queue (`Now`) |

## Skills

| Location | Scope |
|----------|--------|
| `.cursor/skills/` | Project skills (notebook → service promotion) |
| `.agents/skills/after-hours*` | AFK overnight loop + stop/handoff companions |

Config: `.cursor/after-hours-loop.config.json` (`baseBranch: "dev"`, `testCommand: pytest`).

## Guardrails

- Prefer smallest diff that meets acceptance; no drive-by refactors.
- Do not commit `.env` / secrets; respect `safety.pathDenylist`.
- Large new dependency leaps (Google OAuth, PDF engines, frontend test runners) go to **Later** until a human reviews.
- Draft PRs target **`dev`**. Leave `main` as the semi-stable line unless daylight merge is explicit.
- After-hours: stop on dirty tree; never weaken auth/URL guards.
