param(
  [string]$EnvPath = "$HOME\\bot.env"
)

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $ScriptRoot "logs"
$StateDir = Join-Path $ScriptRoot "state"
$LogFile = Join-Path $LogDir "bot_bridge.log"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
New-Item -ItemType Directory -Path $StateDir -Force | Out-Null

if (Test-Path $EnvPath) {
  Get-Content $EnvPath | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $parts = $_.Split('=',2)
    if ($parts.Count -ne 2) { return }
    $k = $parts[0].Trim()
    $v = $parts[1].Trim().Trim('"')
    if ($k) { [Environment]::SetEnvironmentVariable($k, $v, "Process") }
  }
}

if (-not $env:TELEGRAM_BOT_TOKEN -and $env:MIA_BRIDGE_BOT_KEY) {
  $env:TELEGRAM_BOT_TOKEN = $env:MIA_BRIDGE_BOT_KEY
}

$stateFile = Join-Path $StateDir "bot_bridge_state.json"

python "$ScriptRoot\\bot_bridge.py" --env-file "$EnvPath" --state-file "$stateFile" 2>&1 | Tee-Object -FilePath $LogFile -Append
