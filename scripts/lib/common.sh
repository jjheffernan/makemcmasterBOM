#!/usr/bin/env bash
# Shared helpers for scripts/cleanup.sh and scripts/uninstall.sh

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

DRY_RUN=0
VERBOSE=0

log() {
  echo "$@"
}

vlog() {
  if [[ "$VERBOSE" == "1" ]]; then
    echo "$@"
  fi
}

rm_path() {
  local target=$1
  if [[ -e "$target" || -L "$target" ]]; then
    if [[ "$DRY_RUN" == "1" ]]; then
      log "  [dry-run] would remove: $target"
    else
      rm -rf "$target"
      log "  removed: $target"
    fi
  else
    vlog "  (skip, not found) $target"
  fi
}

stop_dev_ports() {
  local port pids
  for port in 8000 8888 5173; do
    pids=$(lsof -ti :"$port" 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
      if [[ "$DRY_RUN" == "1" ]]; then
        log "  [dry-run] would stop process(es) on port $port: $pids"
      else
        log "  stopping process(es) on port $port"
        kill $pids 2>/dev/null || true
        sleep 0.5
      fi
    fi
  done
}

remove_python_caches() {
  log "Python caches and build artifacts"
  find "$ROOT" -type d -name "__pycache__" -not -path "$ROOT/.venv/*" -print0 2>/dev/null \
    | while IFS= read -r -d '' dir; do rm_path "$dir"; done
  rm_path "$ROOT/.pytest_cache"
  rm_path "$ROOT/.coverage"
  rm_path "$ROOT/htmlcov"
  rm_path "$ROOT/build"
  rm_path "$ROOT/dist"
  shopt -s nullglob
  for egg in "$ROOT"/*.egg-info; do
    rm_path "$egg"
  done
  shopt -u nullglob
}

remove_frontend_artifacts() {
  log "Frontend build caches"
  rm_path "$ROOT/frontend/dist"
  rm_path "$ROOT/frontend/.vite"
}

remove_notebook_artifacts() {
  log "Notebook and Jupyter artifacts"
  rm_path "$ROOT/.jupyter"
  find "$ROOT/notebooks" -type d -name ".ipynb_checkpoints" -print0 2>/dev/null \
    | while IFS= read -r -d '' dir; do rm_path "$dir"; done
}

remove_data_caches() {
  log "Notebook data caches (keeping sample_bom.csv and regression_urls.json)"
  local keep=(sample_bom.csv regression_urls.json .gitkeep)
  local base="$ROOT/data"
  if [[ ! -d "$base" ]]; then
    vlog "  (skip, no data/)"
    return
  fi
  local entry name skip
  shopt -s nullglob
  for entry in "$base"/*; do
    name=$(basename "$entry")
    skip=0
    for k in "${keep[@]}"; do
      if [[ "$name" == "$k" ]]; then
        skip=1
        break
      fi
    done
    if [[ "$skip" == "0" ]]; then
      rm_path "$entry"
    fi
  done
  shopt -u nullglob
}

remove_node_modules() {
  log "Node dependencies"
  rm_path "$ROOT/frontend/node_modules"
}

remove_venv() {
  log "Python virtual environment"
  if [[ -x "$ROOT/.venv/bin/playwright" ]]; then
    if [[ "$DRY_RUN" == "1" ]]; then
      log "  [dry-run] would run: .venv/bin/playwright uninstall --all"
    else
      log "  uninstalling Playwright browsers (via project venv)"
      "$ROOT/.venv/bin/playwright" uninstall --all 2>/dev/null || true
    fi
  fi
  rm_path "$ROOT/.venv"
}

remove_playwright_global_cache() {
  log "Playwright browser cache (~/.cache/ms-playwright)"
  if [[ "$DRY_RUN" == "1" ]]; then
    log "  [dry-run] would remove: $HOME/.cache/ms-playwright"
    return
  fi
  rm_path "$HOME/.cache/ms-playwright"
}

usage_header() {
  cat <<EOF
Usage: $1 [OPTIONS]

EOF
}
