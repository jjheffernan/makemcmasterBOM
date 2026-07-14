# References (progressive disclosure)

Load these when the orchestrator needs depth. Orchestrator stays thin: [SKILL.md](../SKILL.md).

| Doc | Status |
|-----|--------|
| [readiness.md](./readiness.md) | Live — agent-ready gates, claim, HITL skip |
| [compatibility.md](./compatibility.md) | Live — soft/hard deps, peer soft-detect, fallbacks |
| [morning-brief.md](./morning-brief.md) | Live — template + write rules (every stop) |
| [state-schema.md](./state-schema.md) | Live — v1 fields, portable queue contract, claim/resume, dry-run |
| [outcomes.md](./outcomes.md) | Live — outcome adapters (`draft-pr`, `doc-artifact`, `branch-only`, `report-only`, `external-ticket-update`); separate from executors |
| [guardrails.md](./guardrails.md) | Live — skip / block / stop / escalate (+ coarse stopReason) |
| [bootstrap.md](./bootstrap.md) | Live — preflight, Sources, dry-run |
| [tick-and-runners.md](./tick-and-runners.md) | Live — sentinel, tick loop, Automation |
| [cloud-ledger.md](./cloud-ledger.md) | Live — optional durable Automation ledger (`cloudLedgerPath`) |
| [run-artifacts.md](./run-artifacts.md) | Live — optional per-tick verification evidence (`runsPath`) |
| [mega-pr.md](./mega-pr.md) | Live — bundled mega-PR; dual-token enable every arm |

Copyable morning brief body: [templates/morning-brief.md](../templates/morning-brief.md).
