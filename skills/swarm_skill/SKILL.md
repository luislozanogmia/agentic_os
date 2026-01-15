---
name: swarm-skill
description: Map and brief Your System' 15-worker swarm using the Cluster→Galaxy→Sun→Planet hierarchy.
allowed-tools: Bash(python3:*), Bash(tmux:*), Read
---

# Swarm Skill

## What This Does
Swarm-skill keeps the Hive Queen aligned with the Cluster → Galaxy → Sun → Planet hierarchy for all 15 workers. Instead of maintaining a persistent JSONL queue, the helper script emits live blueprints, lane summaries, and worker briefs that you can copy into whichever medium the mission requires (plan docs, GitHub issues, Kaggle notebooks, Groq prompts, etc.).

## Files & Locations
- Skill home: `~/.claude/skills/swarm_skill/`
- Blueprint helper: `swarm_controller.py`
- Worker system prompts: `worker_prompts/Wxx.md` (one per worker id)
- Optional worker playbooks: keep them in `~/.claude/swarm_workers/`

## Quick Start
1. **View the hierarchy blueprint**
   ```bash
   python3 ~/.claude/skills/swarm_skill/swarm_controller.py blueprint
   ```
2. **List every worker lane as JSON** (handy for scripts/spreadsheets)
   ```bash
   python3 ~/.claude/skills/swarm_skill/swarm_controller.py lanes
   ```
3. **Cluster coverage matrix**
   ```bash
   python3 ~/.claude/skills/swarm_skill/swarm_controller.py matrix
   ```
4. **Generate a worker brief template** (six-slot lattice enforced, nothing stored)
   ```bash
   python3 ~/.claude/skills/swarm_skill/swarm_controller.py template \
     --worker W04 \
     --cluster "Training Factory" \
     --galaxy "Proto Distillery" \
     --sun "Language Seeds" \
     --planet "Story Extraction" \
     --agent "Worker-Proto" \
     --location "03_reflection_layer" \
     --subject "TinyStories slots" \
     --action "distill" \
     --outcome "proto-japo tuples" \
     --timing "2026-01-08|PT6H" \
     --notes "Feed into your system warmup"
   ```
   The command prints a JSON blob ready to paste into your mission tracker, GitHub issue, Kaggle notebook, or Groq prompt.
5. **Fire a Groq completion using the template output**
   ```bash
   # Ensure GROQ_API_KEY is set in ~/.env (e.g., GROQ_API_KEY=sk_...)
   python3 ~/.claude/skills/swarm_skill/swarm_controller.py groq \
     --model llama-3.1-70b-versatile \
     --prompt "$(cat /tmp/worker_prompt.txt)"
   ```
   The helper loads `GROQ_API_KEY` from `{{HOME}}/.env` (or the live environment) and prints the Groq response. Add `--raw` to see the entire JSON payload.

## Worker Patterns
- **Local bash/python workers**: Use `lanes` to bootstrap tmux panes or supervisor configs—each row already includes the canonical lane name.
- **Groq/Kaggle bursts**: Embed the `template` output as metadata so external services know which cluster/galaxy/sun/planet they are serving.
- **Groq direct calls**: `swarm_controller.py groq --prompt "...prompt..."` routes a structured request to Groq using the key in `.env`, great for quick drafts or evaluator passes.
- **Browser automation**: When a planet requires UI control, generate a template with `planet="Browser Bridge"` and route it to Agent for chrome-control or ax-executor work.
- **Direct worker activation**: When running one worker (W08, W16, etc.) do NOT call `/swarm_skill` inside that session. Instead, paste the worker’s `worker_prompts/Wxx.md` brief directly so the agent embodies the worker role without trying to orchestrate another swarm.

## Tmux Worker Shells
Use tmux whenever you need long-lived worker consoles (Claude Code, Codex CLI, etc.) without juggling macOS windows.

1. **Create a session**  
   ```bash
   tmux new -d -s claude_tmux
   ```
2. **Enter the repo**  
   ```bash
   tmux send-keys -t claude_tmux 'cd ~/.claude' C-m
   ```
3. **Launch the worker**  
   - Claude Code: `tmux send-keys -t claude_tmux 'claude' C-m`
   - Codex CLI: `tmux send-keys -t codex_tmux 'codex' C-m`
4. **Handle trust prompts** (Claude Code asks to trust the folder)  
   ```bash
   tmux send-keys -t claude_tmux '1' C-m
   tmux send-keys -t claude_tmux C-m   # extra Enter to confirm
   ```
5. **Interact without screenshots**  
   - Send commands: `tmux send-keys -t claude_tmux "prompt goes here" C-m`
   - Capture output: `tmux capture-pane -pt claude_tmux | tail -n 80`
   - Attach locally when you want keyboard control: `tmux attach -t claude_tmux`
   - From Codex CLI, you can fire a bare Enter with  
     ```bash
     /bin/zsh -lc '"/opt/homebrew/bin/tmux send-keys -t claude_tmux C-m"'
     ```

Repeat the pattern per worker (e.g., `tmux new -d -s w16_lab`) so each lane has a persistent console that Codex or Claude can drive headlessly.

## Slot Lattice
```
Agent | Location | Subject | Action | Outcome | Timing
```
This six-slot spine keeps every worker aligned with the Cluster → Galaxy → Sun → Planet stack without mandating a specific queue implementation.

## When to Use This Skill
- Rebalancing Your System' worker responsibilities after a pivot.
- Preparing assignments for free-tier bursts (Groq, Kaggle, RTX laptop) without maintaining a stateful queue.
- Checking that each cluster is covered before going offline.
- Drafting structured prompts for the Hive Queen, Claude, or autonomous scripts.
