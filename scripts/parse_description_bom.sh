#!/usr/bin/env bash
# Wrapper for scripts/parse_description_bom.py (uses project venv when present)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi
exec "$PY" "$ROOT/scripts/parse_description_bom.py" "$@"
