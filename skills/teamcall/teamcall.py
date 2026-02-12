#!/usr/bin/env python3
"""Local Codex-Claude ping-pong bridge."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

VALID_AGENTS = {"codex", "claude"}


def now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def trim(text: str, limit: int = 800) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "... [truncated]"


def parse_last_json_line(output: str) -> dict | None:
    parsed = None
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            parsed = value
    return parsed


def codex_reply(prompt: str, thread_id: str | None, args: argparse.Namespace) -> tuple[str, str | None]:
    if thread_id:
        cmd = [
            "codex",
            "-C",
            args.codex_cwd,
            "exec",
            "resume",
            "--json",
            "--skip-git-repo-check",
        ]
        if args.codex_model:
            cmd.extend(["--model", args.codex_model])
        cmd.extend([thread_id, prompt])
    else:
        cmd = [
            "codex",
            "-C",
            args.codex_cwd,
            "exec",
            "--json",
            "--skip-git-repo-check",
        ]
        if args.codex_model:
            cmd.extend(["--model", args.codex_model])
        cmd.append(prompt)

    try:
        run = subprocess.run(
            cmd,
            cwd=args.codex_cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return "Codex CLI not found in PATH.", thread_id

    combined = "\n".join([run.stdout or "", run.stderr or ""])
    next_thread = thread_id
    messages: list[str] = []

    for line in combined.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError:
            continue

        if event.get("type") == "thread.started":
            candidate = event.get("thread_id")
            if isinstance(candidate, str) and candidate:
                next_thread = candidate

        if event.get("type") == "item.completed":
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    messages.append(text.strip())

    if messages:
        return "\n\n".join(messages), next_thread

    tail = "\n".join((combined or "").splitlines()[-8:])
    if run.returncode != 0:
        return f"Codex command failed (exit {run.returncode}).\n{tail}", next_thread
    return f"Codex returned no assistant text.\n{tail}", next_thread


def claude_reply(prompt: str, session_id: str | None, args: argparse.Namespace) -> tuple[str, str | None]:
    cmd = ["claude", "-p", "--output-format", "json"]
    if args.claude_model:
        cmd.extend(["--model", args.claude_model])
    if session_id:
        cmd.extend(["--resume", session_id])
    cmd.append(prompt)

    try:
        run = subprocess.run(
            cmd,
            cwd=args.claude_cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return "Claude CLI not found in PATH.", session_id

    combined = "\n".join([run.stdout or "", run.stderr or ""])
    payload = parse_last_json_line(combined)
    if not payload:
        tail = "\n".join((combined or "").splitlines()[-8:])
        return f"Claude output was not JSON.\n{tail}", session_id

    next_session = payload.get("session_id")
    if not isinstance(next_session, str) or not next_session:
        next_session = session_id

    reply = payload.get("result")
    if not isinstance(reply, str) or not reply.strip():
        reply = "Claude returned no text."

    if payload.get("is_error") or run.returncode != 0:
        subtype = payload.get("subtype") or "unknown_error"
        reply = f"Claude command reported an error ({subtype}).\n{reply}"

    return reply.strip(), next_session


def run_agent(
    agent: str,
    prompt: str,
    codex_thread_id: str | None,
    claude_session_id: str | None,
    args: argparse.Namespace,
) -> tuple[str, str | None, str | None]:
    if agent == "codex":
        reply, next_thread = codex_reply(prompt, codex_thread_id, args)
        return reply, next_thread, claude_session_id
    reply, next_session = claude_reply(prompt, claude_session_id, args)
    return reply, codex_thread_id, next_session


def build_prompt(sender: str, receiver: str, message: str, max_words: int) -> str:
    return (
        "teamcall ping-pong message. "
        "Reply in one concise sentence. "
        "Do not use tools or run commands. "
        f"sender={sender}. receiver={receiver}. "
        f"max_words={max_words}. "
        f"incoming_message={trim(message)}"
    )


def default_output_path(explicit_output: str) -> Path:
    if explicit_output:
        return Path(explicit_output).expanduser()
    return Path(__file__).resolve().parent / "logs" / "teamcall_latest.log"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local Codex-Claude ping-pong bridge.")
    parser.add_argument("--from-agent", "--from", dest="from_agent", choices=sorted(VALID_AGENTS), required=True)
    parser.add_argument("--to-agent", "--to", dest="to_agent", choices=sorted(VALID_AGENTS), required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--turns", type=int, default=1)
    parser.add_argument("--max-words", type=int, default=30)
    parser.add_argument("--output", default="")
    parser.add_argument("--codex-cwd", default=os.getcwd())
    parser.add_argument("--claude-cwd", default=os.getcwd())
    parser.add_argument("--codex-model", default="")
    parser.add_argument("--claude-model", default="")
    parser.add_argument("--from-session-id", default="")
    parser.add_argument("--to-session-id", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.from_agent == args.to_agent:
        print("--from-agent and --to-agent must be different.", file=sys.stderr)
        return 2
    if args.turns < 1:
        print("--turns must be >= 1.", file=sys.stderr)
        return 2
    if args.max_words < 5:
        print("--max-words must be >= 5.", file=sys.stderr)
        return 2

    codex_thread_id: str | None = None
    claude_session_id: str | None = None

    if args.from_agent == "codex":
        codex_thread_id = args.from_session_id or None
    else:
        claude_session_id = args.from_session_id or None

    if args.to_agent == "codex":
        codex_thread_id = args.to_session_id or codex_thread_id
    else:
        claude_session_id = args.to_session_id or claude_session_id

    lines: list[str] = []
    lines.append(f"[{now_ts()}] teamcall started")
    lines.append(f"from_agent={args.from_agent}")
    lines.append(f"to_agent={args.to_agent}")
    lines.append(f"turns={args.turns}")
    lines.append(f"seed_message={args.message}")
    lines.append("")

    relay_message = args.message

    for turn in range(1, args.turns + 1):
        sender_prompt = build_prompt(args.from_agent, args.to_agent, relay_message, args.max_words)
        sender_reply, codex_thread_id, claude_session_id = run_agent(
            args.from_agent,
            sender_prompt,
            codex_thread_id,
            claude_session_id,
            args,
        )

        receiver_prompt = build_prompt(args.to_agent, args.from_agent, sender_reply, args.max_words)
        receiver_reply, codex_thread_id, claude_session_id = run_agent(
            args.to_agent,
            receiver_prompt,
            codex_thread_id,
            claude_session_id,
            args,
        )

        lines.append(f"TURN {turn} {args.from_agent.upper()}_INPUT: {trim(sender_prompt)}")
        lines.append(f"TURN {turn} {args.from_agent.upper()}_OUTPUT: {trim(sender_reply, 2000)}")
        lines.append(f"TURN {turn} {args.to_agent.upper()}_INPUT: {trim(receiver_prompt)}")
        lines.append(f"TURN {turn} {args.to_agent.upper()}_OUTPUT: {trim(receiver_reply, 2000)}")
        lines.append(f"TURN {turn} CODEX_THREAD_ID: {codex_thread_id or 'none'}")
        lines.append(f"TURN {turn} CLAUDE_SESSION_ID: {claude_session_id or 'none'}")
        lines.append("")

        relay_message = receiver_reply

    lines.append(f"[{now_ts()}] teamcall completed")
    lines.append(f"final_codex_thread_id={codex_thread_id or 'none'}")
    lines.append(f"final_claude_session_id={claude_session_id or 'none'}")

    output_path = default_output_path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_text = "\n".join(lines) + "\n"
    output_path.write_text(output_text)

    print(output_text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
