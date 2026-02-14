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

$TELEGRAM_BOT_TOKEN = Ask "Telegram bot token (TELEGRAM_BOT_TOKEN)" ""
$BOT_ALLOWED_TELEGRAM_CHAT_IDS = Ask "Allowed Telegram chat IDs (comma separated, optional)" ""

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
  "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN",
  "BOT_ALLOWED_TELEGRAM_CHAT_IDS=$BOT_ALLOWED_TELEGRAM_CHAT_IDS",
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
