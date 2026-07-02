#!/usr/bin/env bash
# Bundle offline BOM/catalog validators (no live network).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python3"
if [[ ! -x "$PY" ]]; then
  PY="${PYTHON:-python3}"
fi
FIXTURE="${ROOT}/tests/fixtures/description_mega_python.txt"
SAMPLE_BOM="${ROOT}/data/sample_bom.csv"

echo "== check_bom_quantities =="
"$PY" scripts/check_bom_quantities.py "$FIXTURE"

echo "== check_bom_specifications (sample BOM) =="
"$PY" scripts/check_bom_specifications.py "$SAMPLE_BOM"

echo "== check_hardware_specs (matched mega python) =="
PARTS_JSON="$("$PY" -c "
import json
from pathlib import Path
from backend.services.description_bom import parts_from_description
from backend.services.matcher import match_parts
text = Path('$FIXTURE').read_text()
print(json.dumps([p.model_dump() for p in match_parts(parts_from_description(text))]))
")"
echo "$PARTS_JSON" | "$PY" scripts/check_hardware_specs.py --match

echo "== spreadsheet regression =="
"$PY" -m pytest tests/test_spreadsheet_regression.py -q

echo "== check_catalog_integrity =="
"$PY" scripts/check_catalog_integrity.py

echo "== mcmaster cross-test (offline) =="
"$PY" scripts/mcmaster_cross_test.py

echo "== query accuracy fixture =="
"$PY" -m pytest tests/test_query_accuracy.py -q

echo "== notebook ↔ pipeline parity =="
"$PY" -m pytest tests/test_notebook_pipeline_parity.py -q

echo "== feedback API + dispatch =="
"$PY" -m pytest tests/test_feedback.py tests/test_feedback_dispatch.py -q

echo "All checks passed."
