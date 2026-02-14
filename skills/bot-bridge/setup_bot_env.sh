#!/usr/bin/env bash
set -euo pipefail

ENV_PATH="${BOT_ENV_FILE:-$HOME/bot.env}"

echo "Bot bridge env setup"
echo "Target file: $ENV_PATH"

if [[ -f "$ENV_PATH" ]]; then
  read -r -p "bot.env already exists. Overwrite? [y/N] " overwrite
  if [[ ! "$overwrite" =~ ^[Yy]$ ]]; then
    echo "Canceled."
    exit 0
  fi
fi

ask_default() {
  local prompt="$1"
  local default_value="$2"
  local output
  read -r -p "$prompt [$default_value]: " output
  if [[ -z "$output" ]]; then
    output="$default_value"
  fi
  printf '%s' "$output"
}

read_secret() {
  local prompt="$1"
  local output
  read -r -s -p "$prompt: " output
  echo
  printf '%s' "$output"
}

BOT_LLM_BASE_URL="$(ask_default 'LLM base URL (OpenAI compatible)' 'https://api.openai.com/v1')"
BOT_LLM_MODEL="$(ask_default 'LLM model' 'gpt-4o-mini')"
BOT_LLM_SYSTEM_PROMPT="$(ask_default 'System prompt' 'You are a concise helpful assistant responding in plain text.')"
BOT_LLM_API_KEY="$(read_secret 'LLM API key (BOT_LLM_API_KEY)')"

MIA_BRIDGE_BOT_KEY="$(read_secret 'Telegram bot key (MIA_BRIDGE_BOT_KEY, optional)')"
BOT_ALLOWED_TELEGRAM_CHAT_IDS="$(ask_default 'Allowed Telegram chat IDs (comma separated, optional)' '')"

BOT_WHATSAPP_ENABLED_INPUT="$(ask_default 'Enable WhatsApp via Twilio? (1/0)' '0')"
if [[ "$BOT_WHATSAPP_ENABLED_INPUT" == "1" ]]; then
  BOT_WHATSAPP_ENABLED="1"
  TWILIO_ACCOUNT_SID="$(ask_default 'Twilio Account SID' '')"
  TWILIO_AUTH_TOKEN="$(read_secret 'Twilio Auth Token')"
  TWILIO_WHATSAPP_NUMBER="$(ask_default 'Twilio WhatsApp number (example: whatsapp:+14155238886)' '')"
  BOT_ALLOWED_WHATSAPP_SENDERS="$(ask_default 'Allowed WhatsApp senders (comma separated, optional)' '')"
else
  BOT_WHATSAPP_ENABLED="0"
  TWILIO_ACCOUNT_SID=""
  TWILIO_AUTH_TOKEN=""
  TWILIO_WHATSAPP_NUMBER=""
  BOT_ALLOWED_WHATSAPP_SENDERS=""
fi

BOT_POLL_SECONDS="$(ask_default 'Poll interval seconds' '2')"
BOT_TELEGRAM_POLL_TIMEOUT="$(ask_default 'Telegram long-poll timeout seconds' '20')"

mkdir -p "$(dirname "$ENV_PATH")"
cat > "$ENV_PATH" <<EOF
# Bot bridge runtime configuration
# Created by setup_bot_env.sh on $(date '+%Y-%m-%d %H:%M:%S')

BOT_LLM_BASE_URL=$BOT_LLM_BASE_URL
BOT_LLM_API_KEY=$BOT_LLM_API_KEY
BOT_LLM_MODEL=$BOT_LLM_MODEL
BOT_LLM_SYSTEM_PROMPT=$BOT_LLM_SYSTEM_PROMPT

MIA_BRIDGE_BOT_KEY=$MIA_BRIDGE_BOT_KEY
BOT_ALLOWED_TELEGRAM_CHAT_IDS=$BOT_ALLOWED_TELEGRAM_CHAT_IDS

BOT_WHATSAPP_ENABLED=$BOT_WHATSAPP_ENABLED
TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN
TWILIO_WHATSAPP_NUMBER=$TWILIO_WHATSAPP_NUMBER
BOT_ALLOWED_WHATSAPP_SENDERS=$BOT_ALLOWED_WHATSAPP_SENDERS

BOT_POLL_SECONDS=$BOT_POLL_SECONDS
BOT_TELEGRAM_POLL_TIMEOUT=$BOT_TELEGRAM_POLL_TIMEOUT
EOF

chmod 600 "$ENV_PATH"
echo "Saved: $ENV_PATH"
echo "Next: run ./run_bot_bridge.sh or ./run_bot_bar.sh"
