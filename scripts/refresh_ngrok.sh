#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUN_DIR="$ROOT_DIR/.run"
mkdir -p "$RUN_DIR"

PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
UVICORN_BIN="$ROOT_DIR/.venv/bin/uvicorn"
API_URL_LOCAL="http://localhost:8000"

if [[ ! -x "$PYTHON_BIN" || ! -x "$UVICORN_BIN" ]]; then
  echo "Virtualenv not found. Expected .venv/bin/python and .venv/bin/uvicorn."
  exit 1
fi

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  echo ".env not found."
  exit 1
fi

API_KEY="$(grep -E '^AGENT_MEMORY_API_KEY=' "$ROOT_DIR/.env" | tail -n 1 | cut -d '=' -f 2-)"

if [[ -z "$API_KEY" ]]; then
  echo "WARNING: AGENT_MEMORY_API_KEY is empty. APEX will call the API without X-API-Key."
fi

health_check() {
  if [[ -n "$API_KEY" ]]; then
    curl -fsS -H "X-API-Key: $API_KEY" "$API_URL_LOCAL/health" >/dev/null
  else
    curl -fsS "$API_URL_LOCAL/health" >/dev/null
  fi
}

if ! health_check; then
  echo "Starting FastAPI on port 8000..."
  nohup "$UVICORN_BIN" api:app --host 0.0.0.0 --port 8000 --reload > "$RUN_DIR/uvicorn.log" 2>&1 &
  echo "$!" > "$RUN_DIR/uvicorn.pid"

  for _ in {1..30}; do
    if health_check; then
      break
    fi
    sleep 1
  done
fi

if ! health_check; then
  echo "FastAPI did not become healthy. Check $RUN_DIR/uvicorn.log"
  exit 1
fi

get_ngrok_url() {
  curl -fsS http://127.0.0.1:4040/api/tunnels 2>/dev/null | "$PYTHON_BIN" -c "
import json
import sys

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)

for tunnel in payload.get('tunnels', []):
    public_url = tunnel.get('public_url', '')
    config_addr = tunnel.get('config', {}).get('addr', '')
    if public_url.startswith('https://') and config_addr.endswith(':8000'):
        print(public_url)
        break
"
}

NGROK_URL="$(get_ngrok_url || true)"

if [[ -z "$NGROK_URL" ]]; then
  echo "Starting ngrok tunnel to port 8000..."
  nohup ngrok http 8000 > "$RUN_DIR/ngrok.log" 2>&1 &
  echo "$!" > "$RUN_DIR/ngrok.pid"

  for _ in {1..30}; do
    NGROK_URL="$(get_ngrok_url || true)"
    if [[ -n "$NGROK_URL" ]]; then
      break
    fi
    sleep 1
  done
fi

if [[ -z "$NGROK_URL" ]]; then
  echo "Could not read ngrok public URL. Check $RUN_DIR/ngrok.log"
  exit 1
fi

if [[ -n "$API_KEY" ]]; then
  curl -fsS -H "X-API-Key: $API_KEY" "$NGROK_URL/health" >/dev/null
else
  curl -fsS "$NGROK_URL/health" >/dev/null
fi

echo
echo "FastAPI local URL:"
echo "$API_URL_LOCAL"
echo
echo "ngrok public URL:"
echo "$NGROK_URL"
echo
echo "APEX initialization block:"
echo "begin"
echo "    :G_AGENT_MEMORY_API_URL := '$NGROK_URL';"
echo "    :G_AGENT_MEMORY_API_KEY := '$API_KEY';"
echo "end;"
echo
echo "Test URLs:"
echo "$NGROK_URL/health"
echo "$NGROK_URL/docs"
