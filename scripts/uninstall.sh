#!/usr/bin/env bash
# Full uninstall: venv, node_modules, caches, optional Playwright browsers.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

WITH_PLAYWRIGHT=0
ASSUME_YES=0

usage() {
  usage_header "$(basename "$0")"
  cat <<EOF
Remove all local installs and generated files for this project.

Always removes:
  - .venv (Python packages)
  - frontend/node_modules
  - frontend/dist, caches, pytest/jupyter artifacts
  - notebook caches in data/ (keeps sample_bom.csv, regression_urls.json)

Also stops dev servers on ports 8000, 8888, and 5173.

Options:
  --with-playwright   Also remove ~/.cache/ms-playwright (shared browser download,
                      ~150MB+; affects other Playwright projects on this machine)
  --yes, -y           Do not prompt for confirmation
  --dry-run           Print what would be removed without deleting
  --verbose           Show skipped paths
  -h, --help          Show this help

Examples:
  ./scripts/uninstall.sh
  ./scripts/uninstall.sh --yes
  ./scripts/uninstall.sh --yes --with-playwright
  ./scripts/uninstall.sh --dry-run
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-playwright) WITH_PLAYWRIGHT=1; shift ;;
    --yes|-y) ASSUME_YES=1; shift ;;
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

log "MakerWorld BOM uninstall (root: $ROOT)"
log ""
log "This will remove:"
log "  - Python venv (.venv)"
log "  - Node modules (frontend/node_modules)"
log "  - Build caches, test caches, notebook checkpoints"
log "  - Downloaded BOM files in data/ (except tracked samples)"
if [[ "$WITH_PLAYWRIGHT" == "1" ]]; then
  log "  - Playwright browsers (~/.cache/ms-playwright)"
fi
log ""

if [[ "$ASSUME_YES" != "1" && "$DRY_RUN" != "1" ]]; then
  read -r -p "Continue? [y/N] " reply
  if [[ ! "$reply" =~ ^[Yy]$ ]]; then
    log "Cancelled."
    exit 0
  fi
fi

if [[ "$DRY_RUN" == "1" ]]; then
  log "Dry run — nothing will be deleted"
  log ""
fi

stop_dev_ports
remove_python_caches
remove_frontend_artifacts
remove_notebook_artifacts
remove_data_caches
remove_node_modules
remove_venv

if [[ "$WITH_PLAYWRIGHT" == "1" ]]; then
  remove_playwright_global_cache
fi

log ""
if [[ "$DRY_RUN" == "1" ]]; then
  log "Done (dry run)."
else
  log "Uninstall complete."
  log "To reinstall: pip install -e \".[dev,playwright]\" && cd frontend && npm install"
fi
