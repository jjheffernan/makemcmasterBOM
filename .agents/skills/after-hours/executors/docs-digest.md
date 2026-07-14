# Executor: `docs-digest`

Produce a **durable in-repo digest** from an agent-ready research/docs item — **no product code**, **no PR by default**.

Use when `executor` / `executorHint` is `docs-digest`, or Sources name this executor. Prefer this over `research-only` when the night goal is a committed (or checkout-local) doc artifact **without** opening a draft PR. Keep `research-only` for research writeups that prefer `draft-pr` (or issue-comment fallback).

## Soft tools

- Soft-read linked briefs, issue bodies, Notes, `CONTEXT.md` / `docs/adr/*` if present — do **not** rewrite ownership docs unless acceptance explicitly names that path.
- Soft-use a `/research` subagent if present; fold findings into the digest file.
- Soft-read ponytail only if an unexpected code path appears — then **stop** and hand off; this executor stays docs-only.

## Deliverable (`doc-artifact` outcome)

1. Resolve output path:
   - Prefer an explicit path in `acceptance` / Notes / Sources (`write to docs/…`).
   - Else default: `docs/after-hours/<safe-id>-digest.md` where `<safe-id>` is the item `id` with `:` → `-` (e.g. `github-52-digest.md`).
2. Write a short digest: source refs, findings, open questions, explicit “not decided overnight” list. Match acceptance; do not invent product decisions.
3. Publish via [outcome adapter](../references/outcomes.md) **`doc-artifact`** (default): record the path in item `notes`; do **not** open a PR.
4. Only run `draft-pr` if Sources / queue set `outcomeKind: draft-pr` (or bootstrap explicitly requests a PR). Then follow [outcomes.md](../references/outcomes.md) `draft-pr` after the digest exists. Use **`report-only`** when the night should summarize without writing a durable path; **`branch-only`** when the digest should land on a pushed branch without a PR.

A→Z for this executor = digest written at the resolved path + `doc-artifact` recorded — **not** “opened a PR.”

## Out of scope

- Implementing product / feature code
- Opening a PR unless `outcomeKind: draft-pr` was requested
- Answering HITL / inventing roadmap or API choices
- Rewriting CONTEXT/ADRs as ownership changes
- Touching secrets / auth-weakening paths ([guardrails](../references/guardrails.md))

If Notes ask for product implementation, hand off to `pr-slice` / `feature-build`. If the item needs a research PR path, use `research-only`.

## Tests

No product test suite. Optional: cheap docs/link check if the repo already has one; failure → residual risk, do not invent tests overnight.

## Safety checklist

1. No secrets, tokens, `.env` bodies, or credentials in the digest — redact; path pointers only.
2. Denylist check on any path about to be written/committed vs `safety.pathDenylist` — match → **stop loop** escalate ([guardrails](../references/guardrails.md)).
3. Do **not** invent product decisions; mark gaps as open questions / `blocked` if acceptance cannot be met without them.
4. Do not force-push; do not open a PR unless `outcomeKind` requires it.
5. Keep edits to the digest path (+ incidental index link only if acceptance asks).

## Outcome

| Result | Item status |
|--------|-------------|
| Digest at resolved path; `outcomeKind: doc-artifact` recorded (`notes` includes path) | `done` |
| Missing acceptance; needs human decision; cannot place file safely | `blocked` |
| User skip | `skipped` |

Default `outcomeKind: doc-artifact`. Does **not** count toward `maxPrs` unless a requested `draft-pr` was opened.
