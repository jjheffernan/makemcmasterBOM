#!/usr/bin/env bash
# Monthly McMaster taxonomy crawl — polite, fastening-focused, offline validation.
#
# Intended schedule: 1st of each month (see .github/workflows/monthly-taxonomy-crawl.yml
# or a local cron entry documented in docs/backend/mcmaster-taxonomy.md).
#
# Usage:
#   ./scripts/run_monthly_taxonomy_crawl.sh
#   ./scripts/run_monthly_taxonomy_crawl.sh --sync-metacategories
#   MCMASTER_CRAWL_DELAY_SECONDS=8 ./scripts/run_monthly_taxonomy_crawl.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python3"
if [[ ! -x "$PY" ]]; then
  PY="${PYTHON:-python3}"
fi

SYNC_FLAG=()
if [[ "${1:-}" == "--sync-metacategories" ]]; then
  SYNC_FLAG=(--sync-metacategories)
fi

echo "== McMaster monthly taxonomy crawl =="
echo "delay: ${MCMASTER_CRAWL_DELAY_SECONDS:-5}s between pages"

if ! "$PY" -c "import playwright" 2>/dev/null; then
  echo "Installing Playwright extra..."
  "$PY" -m pip install -e ".[playwright]"
fi

if ! "$PY" -m playwright install chromium 2>/dev/null; then
  echo "Installing Chromium for Playwright..."
  "$PY" -m playwright install chromium
fi

echo "== crawl (batch mode) =="
"$PY" scripts/crawl_mcmaster_taxonomy.py --batch "${SYNC_FLAG[@]}"

echo "== offline taxonomy validation =="
"$PY" -m pytest tests/test_category_coverage.py -m 'not integration' -q

echo "Monthly taxonomy crawl completed."
