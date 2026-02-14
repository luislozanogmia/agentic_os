# Agentic OS a.k.a. Claude Code or Codex Config 🚀

Configuration template for the Claude Code or Codex. This setup transforms your coding agent to full-desktop operation agent, it will be able to spawm more agents at the same time via swarm_mode, create a mini-wiki for you via the skill research, run your applications as yourself via the desktop automation, and manage its own memory via memory_palace.

## 🧭 Platform Support
- **macOS**: Full support, including status-bar skills.
- **Windows**: Supported for non-AX skills and bridge workflows via `setup.ps1`.
- **Linux**: Most Python-based skills work with small path/process adapters.

## ✨ Key Features

- **7 Core Skills**: UI automation (`ax-executor`), browser control (`chrome-control`), voice communication (`voice-conversation`), local Codex-Claude bridge (`teamcall`), Telegram bot bridge (`bot-bridge`), swarm orchestration.
- **Multi-Modal Interaction**: Voice-first workflow with audio summaries + text responses for natural agent communication.
- **Agentic Workflow**: Implements the "Two Worlds" principle—AI-native operations first, UI only when necessary.
- **Knowledge Systems**: Integrated `memory_palace` and `world_knowledge` templates for persistent, long-term memory.
- **Safety First**: Non-negotiable "NO DESTRUCTIVE ACTIONS" rule baked into the system prompt.
- **Minimal Install**: Optimized for speed (~100MB) without heavy ML dependencies.

## 🛠 Prerequisites

- **OS**: macOS 12+ recommended, Windows supported for core Python workflows.
- **Python**: 3.10+
- **CLI**: [Claude Code](https://claude.ai/code) installed and authenticated.

## 🚀 Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/luislozanogmia/agentic_os.git
   cd agentic_os
   ```

2. **Run the installer**:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```
   On Windows (PowerShell):
   ```powershell
   .\setup.ps1
   ```

3. **Restart Claude Code**:
   ```bash
   claude
   ```

## 📂 Repository Structure

- `config/`: Templates for `CLAUDE.md` and `SKILL.md`.
- `skills/`: Individual skill modules:
  - `ax-executor`: Desktop UI automation via Accessibility framework
  - `chrome-control`: Browser control and navigation
  - `voice-conversation`: Multi-agent voice communication (TTS/STT)
  - `context-rag`: Knowledge retrieval system
  - `teamcall`: Local Codex-Claude ping-pong bridge
  - `bot-bridge`: Telegram bridge to OpenAI-compatible LLM APIs
  - `swarm_skill`: Agent orchestration (Recommended for Codex only, Claude Code now has Agents Team built-in)
- `scripts/`: Core Python utilities for context compression and search.
- `knowledge/`: Templates for building your own persistent memory system.
- `docs/`: Detailed guides for each skill and architectural principle.

## 🤖 Bot Bridge Quick Start

The new `bot-bridge` skill supports:
- Telegram via `TELEGRAM_BOT_TOKEN`
- Any OpenAI-compatible LLM API (custom base URL + API key + model)

Default config file:
- macOS/Linux: `$HOME/bot.env`
- Windows: `%USERPROFILE%\\bot.env`

macOS/Linux:
```bash
cd skills/bot-bridge
./setup_bot_env.sh
./run_bot_bridge.sh
```

Windows:
```powershell
cd skills\bot-bridge
.\setup_bot_env.ps1
.\run_bot_bridge.ps1
```

macOS status bar app:
```bash
cd skills/bot-bridge
./run_bot_bar.sh
```

## ⚖️ License

MIT License. See [LICENSE](LICENSE) for details.
