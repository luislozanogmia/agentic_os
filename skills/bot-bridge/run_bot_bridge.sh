#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/logs"
STATE_DIR="$ROOT_DIR/state"
ENV_FILE="${BOT_ENV_FILE:-$HOME/bot.env}"

mkdir -p "$LOG_DIR" "$STATE_DIR"
exec >> "$LOG_DIR/bot_bridge.log" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] run_bot_bridge.sh starting"

type python3 >/dev/null 2>&1 || { echo "python3 not found in PATH"; exit 2; }

if [[ -f "$ENV_FILE" && -r "$ENV_FILE" ]]; then
  set +e
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  source_rc=$?
  set +a
  set -e
  if [[ $source_rc -ne 0 ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Warning: failed to source $ENV_FILE (exit=$source_rc)"
  fi
elif [[ -f "$ENV_FILE" ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Warning: $ENV_FILE exists but is not readable"
fi

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" && -n "${MIA_BRIDGE_BOT_KEY:-}" ]]; then
  export TELEGRAM_BOT_TOKEN="$MIA_BRIDGE_BOT_KEY"
fi

exec python3 "$ROOT_DIR/bot_bridge.py" \
  --env-file "$ENV_FILE" \
  --state-file "$STATE_DIR/bot_bridge_state.json"
