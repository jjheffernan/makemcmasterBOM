# after-hours-handoff

Opt-in companion to [after-hours-loop](../after-hours-loop/). Writes or refreshes the durable morning brief after a stop.

**Not always-on** — invoke when you want handoff / brief without starting a new overnight loop.

Install with the loop via:

```bash
./scripts/install.sh --with-companions /path/to/project
```

Companions are **not** in `drop-in/` sync (loop-only). See [INSTALL.md](../../INSTALL.md).
