# Skills Documentation

Each skill in this package extends Claude's capabilities with specialized tools.

## 1. ax-executor
**Universal UI Automation**
- **How it works**: Uses the macOS Accessibility framework to find elements by their visible labels.
- **Commands**: 
  - `python3 ~/.claude/skills/ax-executor/ax_executor_skill.py "button name" --click`
- **Key Files**: `ax_executor.py`, `system_info.py`.

## 2. chrome-control
**Browser Impersonation**
- **How it works**: Controls Google Chrome via keyboard shortcuts (`osascript`) and element labels (`ax-executor`).
- **Commands**: Use natural language instructions like "Search for X on Chrome".
- **Key Files**: `SKILL.md` (instructions).

## 3. context-rag
**Knowledge Retrieval**
- **How it works**: Searches your local knowledge base and the web for relevant context.
- **Commands**:
  - `python3 ~/.claude/scripts/search_function.py "query"`
- **Key Files**: `search_function.py`, `contextrag.py`.

## 4. swarm-skill
**Multi-Worker Orchestration**
- **How it works**: Manages a "swarm" of specialized roles using a Cluster → Galaxy → Sun → Planet hierarchy.
- **Commands**:
  - `python3 ~/.claude/skills/swarm_skill/swarm_controller.py blueprint`
- **Key Files**: `swarm_controller.py`.

## 5. search_os
**Unified Search**
- **How it works**: Fast substring matching across all knowledge bases and conversation history.
- **Commands**: Integrated into `search_function.py`.

## 6. teamcall
**Codex-Claude Local Bridge**
- **How it works**: Runs local ping-pong communication between `codex` and `claude` CLIs with explicit sender and receiver routing.
- **Commands**:
  - `python3 ~/.claude/skills/teamcall/teamcall.py --from-agent codex --to-agent claude --message "Quick sync" --turns 1`
- **Key Files**: `skills/teamcall/SKILL.md`, `skills/teamcall/teamcall.py`.

## 7. bot-bridge
**Telegram + WhatsApp Bridge**
- **How it works**: Polls Telegram and Twilio WhatsApp channels, then routes each message to a generic OpenAI-compatible chat completion API.
- **Commands**:
  - `bash ~/.claude/skills/bot-bridge/setup_bot_env.sh`
  - `bash ~/.claude/skills/bot-bridge/run_bot_bridge.sh`
  - `bash ~/.claude/skills/bot-bridge/run_bot_bar.sh` (macOS status bar)
- **Key Files**: `skills/bot-bridge/bot_bridge.py`, `skills/bot-bridge/bot_bar.py`, `skills/bot-bridge/SKILL.md`.
