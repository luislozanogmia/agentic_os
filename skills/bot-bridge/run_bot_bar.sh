#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/logs"

mkdir -p "$LOG_DIR"

exec python3 "$ROOT_DIR/bot_bar.py" >> "$LOG_DIR/bot_bar.log" 2>&1
