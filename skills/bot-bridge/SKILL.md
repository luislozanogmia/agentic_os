---
name: bot-bridge
description: Run a Telegram bot bridge with a generic OpenAI-compatible LLM API backend and optional macOS status bar control.
allowed-tools: Bash(python3:*), Bash(/bin/bash:*), Read, Grep
---

# Bot Bridge

Bridge incoming Telegram messages into a single OpenAI-compatible LLM endpoint.
No Codex CLI or Claude CLI routing is required.

## Files

- `bot_bridge.py`: Main runtime for Telegram + generic LLM API.
- `bot_bar.py`: macOS status bar app with `bot: ON` and `bot: OFF` state.
- `run_bot_bridge.sh`: macOS/Linux launcher.
- `run_bot_bar.sh`: macOS status bar launcher.
- `run_bot_bridge.ps1`, `run_bot_bridge.bat`: Windows launchers.
- `setup_bot_env.sh`, `setup_bot_env.ps1`, `setup_bot_env.bat`: Interactive env setup.

## Environment File

Default env path is:

- macOS/Linux: `$HOME/bot.env`
- Windows: `%USERPROFILE%\\bot.env`

Required core values:

- `BOT_LLM_BASE_URL` (example: `https://api.openai.com/v1`)
- `BOT_LLM_API_KEY`
- `BOT_LLM_MODEL`

Telegram values:

- `MIA_BRIDGE_BOT_KEY` or `TELEGRAM_BOT_TOKEN`
- optional `BOT_ALLOWED_TELEGRAM_CHAT_IDS`

## Quick Start

macOS/Linux:

```bash
cd ~/.claude/skills/bot-bridge
./setup_bot_env.sh
./run_bot_bridge.sh
```

Windows:

```powershell
cd $HOME\\.claude\\skills\\bot-bridge
.\\setup_bot_env.ps1
.\\run_bot_bridge.ps1
```

macOS status bar:

```bash
cd ~/.claude/skills/bot-bridge
./run_bot_bar.sh
```
