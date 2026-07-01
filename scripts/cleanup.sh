#!/usr/bin/env bash
# Remove regenerable caches and build artifacts. Keeps .venv and node_modules.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

WITH_DEPS=0

usage() {
  usage_header "$(basename "$0")"
  cat <<EOF
Remove caches, build output, and notebook artifacts from this repo.
Stops dev servers on ports 8000, 8888, and 5173 if running.

By default keeps .venv and frontend/node_modules so you can re-run ./scripts/dev.sh
without reinstalling.

Options:
  --deep          Also remove .venv and frontend/node_modules
  --dry-run       Print what would be removed without deleting
  --verbose       Show skipped paths
  -h, --help      Show this help

Examples:
  ./scripts/cleanup.sh
  ./scripts/cleanup.sh --dry-run
  ./scripts/cleanup.sh --deep
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --deep) WITH_DEPS=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --verbose) VERBOSE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

cd "$ROOT"
log "MakerWorld BOM cleanup (root: $ROOT)"
if [[ "$DRY_RUN" == "1" ]]; then
  log "Dry run — nothing will be deleted"
fi
log ""

stop_dev_ports
remove_python_caches
remove_frontend_artifacts
remove_notebook_artifacts
remove_data_caches

if [[ "$WITH_DEPS" == "1" ]]; then
  remove_node_modules
  remove_venv
fi

log ""
if [[ "$DRY_RUN" == "1" ]]; then
  log "Done (dry run)."
else
  log "Done. For a full teardown including Playwright browsers, run:"
  log "  ./scripts/uninstall.sh"
fi
