#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DEBUG_MODE=0
for arg in "$@"; do
  if [[ "$arg" == "--debug" ]]; then
    DEBUG_MODE=1
  fi
done

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -e ".[dev,playwright]"
fi

# Ensure Playwright Chromium is available for MakerWorld scraping
if ! .venv/bin/python -c "import playwright" 2>/dev/null; then
  .venv/bin/pip install -e ".[playwright]"
fi
if [[ ! -d "$HOME/.cache/ms-playwright/chromium-"* ]] 2>/dev/null; then
  echo "Installing Playwright Chromium (one-time, ~150MB)…"
  .venv/bin/playwright install chromium
fi

UVICORN="$ROOT/.venv/bin/uvicorn"
JUPYTER="$ROOT/.venv/bin/jupyter"

free_port() {
  local port=$1
  local pids
  pids=$(lsof -ti :"$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "Freeing port $port (was in use)"
    kill $pids 2>/dev/null || true
    sleep 1
  fi
}

cleanup() {
  trap - EXIT INT TERM
  [[ -n "${API_PID:-}" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "${WEB_PID:-}" ]] && kill "$WEB_PID" 2>/dev/null || true
  [[ -n "${JUPYTER_PID:-}" ]] && kill "$JUPYTER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

free_port 8000
free_port 8888
free_port 5173

# Avoid Cursor/shell HTTP proxies breaking MakerWorld scrapes
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
export NO_PROXY="*"
export SCRAPER="${SCRAPER:-auto}"

if [[ "$DEBUG_MODE" == "1" ]]; then
  export DEBUG=1
  export VITE_DEBUG=true
  echo "Debug mode enabled (DEBUG=1, VITE_DEBUG=true)"
fi

echo "Starting FastAPI on :8000"
"$UVICORN" backend.main:app --reload --host 127.0.0.1 --port 8000 &
API_PID=$!
sleep 1

if ! curl -sf http://127.0.0.1:8000/api/import/stages >/dev/null; then
  echo "ERROR: API did not start correctly. Check port 8000."
  exit 1
fi

echo "Starting JupyterLab on :8888 (base URL /jupyter, proxied via Vite)"
"$JUPYTER" lab \
  --no-browser \
  --port=8888 \
  --ServerApp.base_url=/jupyter \
  --ServerApp.token='' \
  --ServerApp.password='' \
  --ServerApp.allow_origin='*' \
  --ServerApp.disable_check_xsrf=True \
  --notebook-dir="$ROOT" &
JUPYTER_PID=$!

echo "Starting Vite on :5173"
(cd frontend && npm run dev) &
WEB_PID=$!

echo ""
echo "  App:        http://localhost:5173"
echo "  API:        http://localhost:8000/api/health"
if [[ "$DEBUG_MODE" == "1" ]]; then
  echo "  Debug:      ./scripts/dev.sh --debug (open bug icon in header)"
fi
echo "  Notebooks:  http://localhost:5173/notebooks"
echo "  JupyterLab: http://localhost:5173/jupyter/lab/tree/notebooks"
echo ""
echo "Press Ctrl+C to stop all services."

wait
