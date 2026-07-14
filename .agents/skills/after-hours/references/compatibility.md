# Peer skill compatibility (Matt and others)

after-hours-loop is a **workflow-agnostic AFK orchestrator**. Peer workflows (including Matt’s wayfinder / grill / to-spec / to-tickets skills) are **optional inputs**, not parents. When those artifacts exist, we **detect and consume** them; we never require that pipeline and we do not re-run grilling overnight.

**Refuse:** `/after-hours` **must start** without grill / to-tickets (or any peer chain). Ready work from explicit Sources is enough. Do not design or run a gate that waits on daytime alignment skills before bootstrap.

**Night-time binding is Sources only** — `github-tickets` and `wayfinder-afk` are **opt-in only** (never default night Sources). Uncomment them in a Sources block when wanted; night templates keep them commented. Do not fork the orchestrator for each peer.

Smoke rows (Matt present / absent / mixed Sources): [docs/smoke-matrix.md](https://github.com/jjheffernan/heff-skills/blob/main/docs/smoke-matrix.md).

## Soft vs hard deps (ADR-0001 style)

| Kind | Artifacts | Rule |
|------|-----------|------|
| **Soft** | `CONTEXT.md`, `docs/adr/*`, `docs/agents/issue-tracker.md`, ponytail / implement / tdd / code-review if installed | If present: soft-read or use. If absent: continue. Never rewrite CONTEXT/ADRs overnight. |
| **Hard** | Agent-ready work items in the queue | No agent-ready work → **stop** after preflight / empty-queue path. Do not invent tickets. |

Soft deps are context and discipline. Hard dep is a non-empty executable queue (unless `allowEmptyQueue` for dry-run/noop — see [bootstrap.md](./bootstrap.md)).

## Soft-detect (every bootstrap / refresh)

Run when peers appear; later steps do not invent Sources the user omitted. **Sources decide what enters the queue.**

1. **`docs/agents/issue-tracker.md`** — if present, follow its claim / label / comment ops instead of inventing a second dialect.
2. **`ready-for-agent` + Agent Brief** — when Sources include labeled GitHub (or tracker) work; prefer Brief over issue body.
3. **Frontier / tickets** — only when Sources include **`github-tickets`** (or another tickets / frontier source); consume ready frontier items with blockers closed ([readiness.md](./readiness.md) gate d).
4. **`wayfinder:map`** — only if Sources include **`wayfinder-afk`**. Then: research / AFK-typed map work only. Never open product PRs from grilling or prototype HITL map nodes.
5. **`CONTEXT.md` / `docs/adr/`** — soft-read; treat as constraints on implementable items.
6. **Native Sources** — `todo-md`, `feature-spec`, labeled `github-issues` as configured.

## Overnight bans

| Action | Allowed? |
|--------|----------|
| Re-grill / start grill-me / grill-with-docs | **No** |
| Resolve wayfinder grilling or prototype HITL tickets | **No** |
| Invent product decisions or new acceptance | **No** |
| Soft-read CONTEXT/ADRs; implement agent-ready tickets | **Yes** |
| Opt-in `wayfinder-afk` research-only work | **Yes** (outcome adapter per item; default research writeup) |

Mention fog that needs daytime alignment in the [morning brief](./morning-brief.md) under Suggested next (grill / wayfinder / briefs tomorrow — human tools, not AHL requirements).

## Fallback when Matt skills absent

1. Queue only what Sources explicitly name (labels, TODO sections, spec paths).
2. Apply [readiness.md](./readiness.md): vague → `blocked` (`needs-info` / `needs-grill`), never invent scope.
3. Soft deps (ponytail etc.): skip; use executor-local steps in `executors/*.md`.
4. Morning brief still writes: “no peer grill artifacts detected” is fine; point humans at daytime alignment if useful.
