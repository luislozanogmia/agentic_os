param(
  [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "Agentic OS Installer (Windows)" -ForegroundColor Green

$ClaudeHome = Join-Path $HOME ".claude"
$DocsPath = Join-Path $HOME "Documents\artificial_minds"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Target: $ClaudeHome"
Write-Host "Knowledge Base: $DocsPath"

if ((Test-Path $ClaudeHome) -and -not $Force) {
  Write-Host "Existing ~/.claude detected. Re-run with -Force if you want overwrite behavior." -ForegroundColor Yellow
}

New-Item -ItemType Directory -Path "$ClaudeHome\skills" -Force | Out-Null
New-Item -ItemType Directory -Path "$ClaudeHome\.chat_history" -Force | Out-Null
New-Item -ItemType Directory -Path $DocsPath -Force | Out-Null

Write-Host "Copying modules..."
Copy-Item "$RepoRoot\skills\*" "$ClaudeHome\skills\" -Recurse -Force
Copy-Item "$RepoRoot\scripts\*.py" "$ClaudeHome\" -Force

function Apply-Template {
  param(
    [string]$Source,
    [string]$Destination
  )

  $content = Get-Content -Raw $Source
  $content = $content.Replace("{{CLAUDE_HOME}}", $ClaudeHome)
  $content = $content.Replace("{{DOCS_PATH}}", $DocsPath)
  $content = $content.Replace("{{HOME}}", $HOME)
  Set-Content -Path $Destination -Value $content -Encoding UTF8
}

Write-Host "Configuring templates..."
Apply-Template "$RepoRoot\config\CLAUDE.md.template" "$ClaudeHome\CLAUDE.md"
Copy-Item "$RepoRoot\config\SKILL.md" "$ClaudeHome\SKILL.md" -Force
Apply-Template "$RepoRoot\knowledge\memory_palace.md.template" "$DocsPath\memory_palace.md"
Copy-Item "$RepoRoot\knowledge\world_knowledge.md.template" "$DocsPath\world_knowledge.md" -Force

Get-ChildItem -Path $ClaudeHome -Recurse -Filter "*.py" | ForEach-Object {
  $c = Get-Content -Raw $_.FullName
  $c = $c.Replace("{{CLAUDE_HOME}}", $ClaudeHome)
  Set-Content -Path $_.FullName -Value $c -Encoding UTF8
}

$VenvPython = Join-Path $ClaudeHome ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
  Write-Host "Creating virtual environment..."
  python -m venv "$ClaudeHome\.venv"
}

Write-Host "Installing dependencies..."
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r "$RepoRoot\requirements.txt"

$EnvFile = Join-Path $ClaudeHome ".env"
if (-not (Test-Path $EnvFile)) {
  @(
    "GROQ_API_KEY=",
    "OPENAI_API_KEY="
  ) | Set-Content -Path $EnvFile -Encoding UTF8
  Write-Host "Created empty $EnvFile" -ForegroundColor Yellow
}

$BotSetup = "$RepoRoot\skills\bot-bridge\setup_bot_env.ps1"
if (Test-Path $BotSetup) {
  $answer = Read-Host "Configure $HOME\\bot.env for bot-bridge now? (y/N)"
  if ($answer.ToLower() -eq "y") {
    & $BotSetup
  }
}

Write-Host "Installation complete." -ForegroundColor Green
Write-Host "Restart Claude Code to apply changes."
