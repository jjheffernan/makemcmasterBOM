# Executor: `ops-checklist`

Process an **ops / triage checklist** or labeled queue digest — **no product code**, **no PR by default**.

Use when `executor` / `executorHint` is `ops-checklist`, or Sources name this executor. Prefer this over `docs-digest` when the night goal is labeling, triage queue walk-through, or an ops process checklist (not research synthesis). Prefer `docs-digest` for research/docs digests; hand product implementation to `pr-slice` / `feature-build`.

## Soft tools

- Soft-read linked briefs, issue lists, Notes, `CONTEXT.md` / `docs/adr/*` if present — do **not** rewrite ownership docs unless acceptance explicitly names that path.
- Soft-use tracker APIs (`gh issue list`, label filters) only to **read** and summarize; do not invent assignment / close policy overnight.
- Soft-read ponytail only if an unexpected code path appears — then **stop** and hand off; this executor stays ops/docs-only.

## Deliverable (default: no code PR)

Preferred outcomes ([outcomes.md](../references/outcomes.md)):

| `outcomeKind` | When |
|---------------|------|
| `report-only` | Findings land in morning brief / chat only — **default** |
| `doc-artifact` | Durable in-repo triage/ops digest when Sources / acceptance ask for a file |

1. Walk the checklist / labeled queue per acceptance; summarize queue snapshot, labels / readiness notes, suggested next human actions, and an explicit “not decided overnight” list. Do not invent process or product decisions.
2. Publish via outcome adapter:
   - Default **`report-only`**: no git publish; record a short pointer in item `notes`; include findings in the morning brief.
   - When Sources / acceptance set `outcomeKind: doc-artifact` → write `docs/after-hours/<safe-id>-ops.md` (or acceptance path) and record the path in `notes`.
3. Only run `draft-pr` if Sources / queue explicitly set `outcomeKind: draft-pr`. Do **not** invent a PR for ops/triage nights.

A→Z for this executor = checklist/digest complete + chosen non-PR adapter recorded — **not** “opened a PR.”

## Out of scope

- Implementing product / feature code
- Opening a PR unless `outcomeKind: draft-pr` was requested
- Closing / reassigning issues or inventing triage policy overnight
- Answering HITL / inventing roadmap or API choices
- Rewriting CONTEXT/ADRs as ownership changes
- Touching secrets / auth-weakening paths ([guardrails](../references/guardrails.md))

If Notes ask for product implementation, hand off to `pr-slice` / `feature-build`. If the item needs a research writeup PR, use `research-only`. For a research/docs digest without triage framing, use `docs-digest`.

## Tests

No product test suite. Optional: cheap docs/link check if the repo already has one; failure → residual risk, do not invent tests overnight.

## Safety checklist

1. No secrets, tokens, `.env` bodies, or credentials in the digest/report — redact; path pointers only.
2. Denylist check on any path about to be written/committed vs `safety.pathDenylist` — match → **stop loop** escalate ([guardrails](../references/guardrails.md)).
3. Do **not** invent process or product decisions; mark gaps as open questions / `blocked` if acceptance cannot be met without them.
4. Do not force-push; do not open a PR unless `outcomeKind` requires it.
5. Keep edits to the ops digest path only when using `doc-artifact` (+ incidental index link only if acceptance asks).

## Outcome

| Result | Item status |
|--------|-------------|
| Checklist/digest complete; `report-only` or `doc-artifact` recorded | `done` |
| Missing acceptance; needs human triage policy; cannot place artifact safely | `blocked` |
| User skip | `skipped` |

Default `outcomeKind: report-only` (no PR). Use `doc-artifact` when Sources ask for a durable file. Does **not** count toward `maxPrs` unless a requested `draft-pr` was opened.

## Bootstrap

Bind via `executorHint: ops-checklist`, Sources override (`github:52 executor:ops-checklist`), or queue `executor: ops-checklist`. See [bootstrap.md](../references/bootstrap.md).
