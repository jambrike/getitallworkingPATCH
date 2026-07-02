#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export COMPANION_URL="${COMPANION_URL:-http://127.0.0.1:8765}"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "Missing OPENAI_API_KEY. Copy .env.example to .env and add your key." >&2
  exit 2
fi

PIDS=()

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      pkill -TERM -P "$pid" 2>/dev/null || true
      kill "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT INT TERM

python3 -m uvicorn agent.companion_service:app \
  --host "${COMPANION_HOST:-127.0.0.1}" \
  --port "${COMPANION_PORT:-8765}" &
SERVICE_PID=$!
PIDS+=("$SERVICE_PID")

sleep 2

(cd "$ROOT_DIR/overlay + TTS" && npm start) &
OVERLAY_PID=$!
PIDS+=("$OVERLAY_PID")

if [[ "${START_VOICE:-0}" == "1" ]]; then
  (
    cd "$ROOT_DIR/voice"
    if [[ -s "$HOME/.nvm/nvm.sh" ]]; then
      # The Vosk npm package depends on an older native binding that builds on Node 16.
      # Keep this scoped to the voice subprocess so the Electron overlay can use normal Node.
      # shellcheck disable=SC1091
      source "$HOME/.nvm/nvm.sh"
      nvm use 16 >/dev/null
    fi
    npm start
  ) &
  VOICE_PID=$!
  PIDS+=("$VOICE_PID")
fi

wait "$OVERLAY_PID"
