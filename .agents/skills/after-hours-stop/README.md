# after-hours-stop

Opt-in companion to [after-hours-loop](../after-hours-loop/). Stops an armed AFK run: kill sentinel, honor stop phrases, ensure morning brief.

**Not always-on** — invoke explicitly (`stop after-hours` / `/after-hours stop`).

Install with the loop via:

```bash
./scripts/install.sh --with-companions /path/to/project
```

Companions are **not** in `drop-in/` sync (loop-only). See [INSTALL.md](../../INSTALL.md).
