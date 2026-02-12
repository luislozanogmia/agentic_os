---
name: teamcall
description: Run local CLI-only communication between Codex and Claude with explicit sender and receiver routing for ping-pong exchanges. Use when we need direct in-house agent-to-agent checks, structured handoffs, or quick coordination loops without Telegram.
allowed-tools: Bash(codex:*), Bash(claude:*), Bash(python3:*), Read, Grep
---

# Teamcall

Run standalone local communication between Codex and Claude.
This skill executes ping-pong messages with explicit routing flags that identify who sends and who receives.

## Quick Start

```bash
python3 ~/.claude/skills/teamcall/teamcall.py \
  --from-agent codex \
  --to-agent claude \
  --message "Quick sync: what should we do next?" \
  --turns 1
```

## Required Routing Flags

- `--from-agent codex|claude`
- `--to-agent codex|claude`
- `--message "<seed message>"`

The two agents must be different for each run.

## Session Continuity

To continue on existing sessions:

```bash
python3 ~/.claude/skills/teamcall/teamcall.py \
  --from-agent codex \
  --to-agent claude \
  --from-session-id <codex_thread_id> \
  --to-session-id <claude_session_id> \
  --message "Continue from previous handoff." \
  --turns 2
```

## Notes

- Teamcall is local-only and does not call Telegram APIs.
- Codex path uses `codex exec --json` and `codex exec resume --json`.
- Claude path uses `claude -p --output-format json` and `--resume`.
- Output defaults to `~/.claude/skills/teamcall/logs/teamcall_latest.log` in installed environments.
