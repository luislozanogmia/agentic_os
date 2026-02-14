param(
  [string]$EnvPath = "$HOME\\bot.env"
)

Write-Host "Bot bridge env setup"
Write-Host "Target file: $EnvPath"

if (Test-Path $EnvPath) {
  $overwrite = Read-Host "bot.env already exists. Overwrite? (y/N)"
  if ($overwrite.ToLower() -ne "y") {
    Write-Host "Canceled."
    exit 0
  }
}

function Ask([string]$Prompt, [string]$Default) {
  if ($Default -ne "") {
    $value = Read-Host "$Prompt [$Default]"
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value
  }
  return (Read-Host "$Prompt")
}

$BOT_LLM_BASE_URL = Ask "LLM base URL (OpenAI compatible)" "https://api.openai.com/v1"
$BOT_LLM_MODEL = Ask "LLM model" "gpt-4o-mini"
$BOT_LLM_SYSTEM_PROMPT = Ask "System prompt" "You are a concise helpful assistant responding in plain text."
$BOT_LLM_API_KEY = Ask "LLM API key (BOT_LLM_API_KEY)" ""

$MIA_BRIDGE_BOT_KEY = Ask "Telegram bot key (MIA_BRIDGE_BOT_KEY, optional)" ""
$BOT_ALLOWED_TELEGRAM_CHAT_IDS = Ask "Allowed Telegram chat IDs (comma separated, optional)" ""

$BOT_WHATSAPP_ENABLED = Ask "Enable WhatsApp via Twilio? (1/0)" "0"
if ($BOT_WHATSAPP_ENABLED -eq "1") {
  $TWILIO_ACCOUNT_SID = Ask "Twilio Account SID" ""
  $TWILIO_AUTH_TOKEN = Ask "Twilio Auth Token" ""
  $TWILIO_WHATSAPP_NUMBER = Ask "Twilio WhatsApp number (example: whatsapp:+14155238886)" ""
  $BOT_ALLOWED_WHATSAPP_SENDERS = Ask "Allowed WhatsApp senders (comma separated, optional)" ""
} else {
  $TWILIO_ACCOUNT_SID = ""
  $TWILIO_AUTH_TOKEN = ""
  $TWILIO_WHATSAPP_NUMBER = ""
  $BOT_ALLOWED_WHATSAPP_SENDERS = ""
}

$BOT_POLL_SECONDS = Ask "Poll interval seconds" "2"
$BOT_TELEGRAM_POLL_TIMEOUT = Ask "Telegram long-poll timeout seconds" "20"

$lines = @(
  "# Bot bridge runtime configuration",
  "# Created by setup_bot_env.ps1 on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
  "",
  "BOT_LLM_BASE_URL=$BOT_LLM_BASE_URL",
  "BOT_LLM_API_KEY=$BOT_LLM_API_KEY",
  "BOT_LLM_MODEL=$BOT_LLM_MODEL",
  "BOT_LLM_SYSTEM_PROMPT=$BOT_LLM_SYSTEM_PROMPT",
  "",
  "MIA_BRIDGE_BOT_KEY=$MIA_BRIDGE_BOT_KEY",
  "BOT_ALLOWED_TELEGRAM_CHAT_IDS=$BOT_ALLOWED_TELEGRAM_CHAT_IDS",
  "",
  "BOT_WHATSAPP_ENABLED=$BOT_WHATSAPP_ENABLED",
  "TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID",
  "TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN",
  "TWILIO_WHATSAPP_NUMBER=$TWILIO_WHATSAPP_NUMBER",
  "BOT_ALLOWED_WHATSAPP_SENDERS=$BOT_ALLOWED_WHATSAPP_SENDERS",
  "",
  "BOT_POLL_SECONDS=$BOT_POLL_SECONDS",
  "BOT_TELEGRAM_POLL_TIMEOUT=$BOT_TELEGRAM_POLL_TIMEOUT"
)

$parent = Split-Path -Parent $EnvPath
if (-not (Test-Path $parent)) {
  New-Item -ItemType Directory -Path $parent -Force | Out-Null
}

Set-Content -Path $EnvPath -Value $lines -Encoding UTF8
Write-Host "Saved: $EnvPath"
Write-Host "Next: run run_bot_bridge.ps1"
