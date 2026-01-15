# Claude Code Config (macOS) 🚀

A sophisticated, production-ready configuration for the Claude Code CLI. This setup transforms Claude from a chat interface into a high-speed engine for precision research, desktop automation, and knowledge management.

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
   git clone https://github.com/your-username/claude-code-config.git
   cd claude-code-config
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
