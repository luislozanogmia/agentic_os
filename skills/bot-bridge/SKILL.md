---
name: bot-bridge
description: Run a Telegram bot bridge with OpenAI-compatible or Anthropic-compatible LLM backends, optional agentic tool use, and image vision via MCP.
---

# Bot Bridge

Bridge incoming Telegram messages into an LLM endpoint with optional agentic tools.

Supports two modes:
- **OpenAI mode** (default): Simple chat completion via any OpenAI-compatible API.
- **Anthropic mode**: Agentic tool use loop with web search, file operations, Spotify control, Claude escalation, and image vision via MCP.

## Tested Backends

| Backend | Format | Tools | Image Vision |
|---------|--------|-------|--------------|
| OpenAI / GPT | `openai` | No | No |
| Any OpenAI-compatible API | `openai` | No | No |
| MiniMax M2.5 | `anthropic` | Yes | Yes (via MCP) |
| Claude API | `anthropic` | Yes | No |

## Files

- `bot_bridge.py`: Main runtime for Telegram + LLM API with agentic tools.
- `bot_bar.py`: macOS status bar app with `bot: ON` and `bot: OFF` state.
- `run_bot_bridge.sh`: macOS/Linux launcher.
- `run_bot_bar.sh`: macOS status bar launcher.
- `run_bot_bridge.ps1`, `run_bot_bridge.bat`: Windows launchers.
- `setup_bot_env.sh`, `setup_bot_env.ps1`, `setup_bot_env.bat`: Interactive env setup.

## Environment File

Default env path is:

- macOS/Linux: `$HOME/bot.env`
- Windows: `%USERPROFILE%\bot.env`

### Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_LLM_BASE_URL` | Yes | `https://api.openai.com/v1` | LLM API endpoint |
| `BOT_LLM_API_KEY` | Yes | — | API key |
| `BOT_LLM_MODEL` | Yes | `gpt-4o-mini` | Model name |
| `BOT_LLM_FORMAT` | No | `openai` | `openai` or `anthropic` |
| `BOT_LLM_SYSTEM_PROMPT` | No | Generic assistant | System prompt |
| `TELEGRAM_BOT_TOKEN` | Yes | — | Telegram bot token |
| `BOT_ALLOWED_TELEGRAM_CHAT_IDS` | No | — | Comma-separated allowed chat IDs |

### Spotify Settings (optional, for `anthropic` mode)

| Variable | Required | Description |
|----------|----------|-------------|
| `SPOTIFY_CLIENT_ID` | No | Spotify app client ID |
| `SPOTIFY_CLIENT_SECRET` | No | Spotify app client secret |
| `SPOTIFY_REDIRECT_URL` | No | OAuth redirect URL |

## Agentic Tools (Anthropic mode only)

When `BOT_LLM_FORMAT=anthropic`, the bot exposes 8 tools to the LLM:

- **web_search**: Search the web via DuckDuckGo (requires `ddgs` package)
- **read_file**: Read files from the host machine
- **write_file**: Write files to the host machine
- **list_directory**: List directory contents
- **spotify_play**: Play music on Spotify devices
- **spotify_devices**: List available Spotify Connect devices
- **spotify_search**: Search Spotify tracks
- **ask_claude**: Escalate to Claude CLI for complex reasoning

## Image Vision (MCP)

Photo messages from Telegram are analyzed via MiniMax's MCP server (`minimax-coding-plan-mcp`).

Requirements:
- `uvx` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- `BOT_LLM_API_KEY` must be a valid MiniMax API key
- Works on both Windows and Unix

## Telegram Commands

- `/help` — Show available commands
- `/status` — Show bot status (model, format, endpoint)
- `/clear` — Clear conversation history for this chat

## Quick Start

### MiniMax M2.5 (with agentic tools)

```env
BOT_LLM_BASE_URL=https://api.minimax.io/anthropic
BOT_LLM_API_KEY=your-minimax-key
BOT_LLM_MODEL=MiniMax-M2.5
BOT_LLM_FORMAT=anthropic
BOT_LLM_SYSTEM_PROMPT=You are a helpful family assistant.
TELEGRAM_BOT_TOKEN=your-telegram-token
```

```bash
pip install anthropic ddgs
cd ~/.claude/skills/bot-bridge
python bot_bridge.py
```

### OpenAI (simple mode)

```env
BOT_LLM_BASE_URL=https://api.openai.com/v1
BOT_LLM_API_KEY=your-openai-key
BOT_LLM_MODEL=gpt-4o-mini
TELEGRAM_BOT_TOKEN=your-telegram-token
```

```bash
cd ~/.claude/skills/bot-bridge
python bot_bridge.py
```

### Optional Dependencies

```bash
pip install anthropic   # Required for BOT_LLM_FORMAT=anthropic
pip install ddgs        # Required for web_search tool
```

macOS status bar:

```bash
cd ~/.claude/skills/bot-bridge
./run_bot_bar.sh
```
