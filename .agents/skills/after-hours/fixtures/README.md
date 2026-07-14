# State fixtures

Sample `.cursor/after-hours-loop.state.json` shapes for `scripts/validate-state.py`.

## Valid (exit 0)

| File | Notes |
|------|-------|
| `sample-state.valid.json` | Schema v1, one `open` item, empty `prs`, `priority: github-first` |
| `sample-state.valid-stopped.json` | After a run: `stopReason: budget`, one draft PR, `megaPr: false` |
| `sample-state.valid-todo-first.json` | `priority: todo-first`, `docs-digest` / `doc-artifact` |

## Invalid (exit 1)

| File | Failure |
|------|---------|
| `sample-state.invalid-prs.json` | `prs` entries not objects with `url` |
| `sample-state.invalid-status.json` | `queue[].status` not in allowed set |
| `sample-state.invalid-stopReason.json` | `stopReason` not in `{done, blocked, noop, budget}` |
| `sample-state.invalid-megaPr.json` | `megaPr` non-boolean |
| `sample-state.invalid-priority.json` | `priority` not in `{github-first, fifo, todo-first}` |
| `sample-state.invalid-version.json` | `version` ≠ `1` |
| `sample-state.invalid-missing-baseBranch.json` | missing required `baseBranch` |

From the heff-skills repo root:

```bash
python3 scripts/validate-state.py skills/after-hours-loop/fixtures/sample-state.valid.json
# … and each valid-* / invalid-* fixture via CI (`.github/workflows/ci.yml`)
```

## Harness expectations (stubs OK)

Schema fixtures above do **not** assert parse / write-back. Future harness:

### Parse (Sources → queue)

1. Each Sources line maps to a `sources/*.md` module and materializes portable queue fields.
2. Unknown source types fail closed or materialize `blocked` — never invent tracker IDs.
3. Readiness: non-ready → `blocked` with reason listable in the morning brief.
4. Round-trip: Sources text → queue JSON matches golden shapes.

### Priority

1. `github-first` drains GitHub sources before TODO / feature-spec.
2. `fifo` preserves materialization order.
3. `todo-first` drains TODO before GitHub.
4. Unknown priorities: **now rejected by `validate-state.py`**.

### Write-back

1. TODO auto check-off on `done` when `todo-md` promises it.
2. Idempotent re-run; no cross-source mutation.
3. Non-PR outcomes (`doc-artifact` / `report-only`) do not invent draft PRs for write-back alone.
