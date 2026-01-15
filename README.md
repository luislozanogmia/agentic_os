# Claude Code Config (macOS) 🚀

Configuration template for the Claude Code. This setup transforms Claude from a coding agent to full-desktop operation agent, it will be able to spawm more agents at the same time via swarm_mode, create a mini-wiki for you via the skill research, run your applications as yourself via the desktop automation, and manage its own memory via memory_palace.

## ✨ Key Features

- **6 Core Skills**: Includes UI automation (`ax-executor`), browser control (`chrome-control`), and swarm orchestration.
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
- `skills/`: Individual skill modules (AX, Chrome, RAG, Swarm, etc.).
- `scripts/`: Core Python utilities for context compression and search.
- `knowledge/`: Templates for building your own persistent memory system.
- `docs/`: Detailed guides for each skill and architectural principle.

## ⚖️ License

MIT License. See [LICENSE](LICENSE) for details.
