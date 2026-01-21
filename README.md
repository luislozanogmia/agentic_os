# Agentic OS a.k.a. Claude Code Config (macOS) 🚀

Configuration template for the Claude Code. This setup transforms Claude from a coding agent to full-desktop operation agent, it will be able to spawm more agents at the same time via swarm_mode, create a mini-wiki for you via the skill research, run your applications as yourself via the desktop automation, and manage its own memory via memory_palace.

## 🤔 Not using MacOS?
Ask Claude to create adapters for Windows or Linux for the skills. Since most of the skills are python Claude will just edit the names of the process to gather info from, should take 20-30min. For Windows I tested it and took 20 min, I don't have Linux to test.

## ✨ Key Features

- **7 Core Skills**: UI automation (`ax-executor`), browser control (`chrome-control`), voice communication (`voice-conversation`), swarm orchestration, and more.
- **Multi-Modal Interaction**: Voice-first workflow with audio summaries + text responses for natural agent communication.
- **Agentic Workflow**: Implements the "Two Worlds" principle—AI-native operations first, UI only when necessary.
- **Knowledge Systems**: Integrated `memory_palace` and `world_knowledge` templates for persistent, long-term memory.
- **Safety First**: Non-negotiable "NO DESTRUCTIVE ACTIONS" rule baked into the system prompt.
- **Minimal Install**: Optimized for speed (~100MB) without heavy ML dependencies.

## 🛠 Prerequisites

- **OS**: macOS 12+ (Monterey or later)
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
  - `swarm_skill`: Agent orchestration
  - And more...
- `scripts/`: Core Python utilities for context compression and search.
- `knowledge/`: Templates for building your own persistent memory system.
- `docs/`: Detailed guides for each skill and architectural principle.

## ⚖️ License

MIT License. See [LICENSE](LICENSE) for details.
