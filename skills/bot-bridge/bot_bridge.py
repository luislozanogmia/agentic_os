#!/usr/bin/env python3
"""Telegram bot bridge with a generic LLM backend.

Supports both OpenAI-compatible and Anthropic-compatible APIs.
When using Anthropic format (BOT_LLM_FORMAT=anthropic), enables agentic
tool use with web search, file operations, Spotify control, Claude
escalation, and image vision via MCP.

Tested backends: OpenAI, Codex, Claude API, MiniMax M2.5.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

try:
    import anthropic as _anthropic_sdk
except ImportError:
    _anthropic_sdk = None  # type: ignore

try:
    from ddgs import DDGS as _DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS as _DDGS  # type: ignore
    except ImportError:
        _DDGS = None  # type: ignore

_TOOL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": "Search the web for current information, news, or facts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file on this machine.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or home-relative file path (~ allowed)"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write or overwrite a file on this machine.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write to"},
                "content": {"type": "string", "description": "Text content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_directory",
        "description": "List files and folders in a directory on this machine.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "spotify_play",
        "description": "Play a song or artist on Spotify. Optionally specify a device (e.g. 'Echo Pop', 'Office', 'Everywhere').",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Song name, 'song by artist', or Spotify URL"},
                "device": {"type": "string", "description": "Partial device name to play on (optional)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "spotify_devices",
        "description": "List all available Spotify Connect devices (speakers, Echo, computer, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "spotify_search",
        "description": "Search for tracks on Spotify without playing them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "ask_claude",
        "description": "Escalate a complex question or task to Claude, a more powerful AI agent running on this machine. Use when the task requires deep reasoning, code generation, or expert-level analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The full question or task to send to Claude"},
            },
            "required": ["message"],
        },
    },
]

_MAX_TOOL_TURNS = 6


def _exec_web_search(query: str) -> str:
    if _DDGS is None:
        return "Error: duckduckgo-search package not installed."
    try:
        month_year = datetime.now().strftime("%B %Y")
        enriched_query = f"{query} {month_year}"
        with _DDGS() as ddgs:
            results = list(ddgs.text(enriched_query, max_results=8))
        if not results:
            return "No results found."
        lines = []
        for r in results:
            lines.append(f"**{r.get('title', '')}**\n{r.get('body', '')}\n{r.get('href', '')}")
        return "\n\n".join(lines)
    except Exception as exc:
        return f"Search error: {exc}"


def _exec_read_file(path: str) -> str:
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"File not found: {p}"
        if not p.is_file():
            return f"Not a file: {p}"
        content = p.read_text(encoding="utf-8", errors="replace")
        if len(content) > 8000:
            content = content[:8000] + "\n... (truncated)"
        return content
    except Exception as exc:
        return f"Read error: {exc}"


def _exec_write_file(path: str, content: str) -> str:
    try:
        p = Path(path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"File written: {p}"
    except Exception as exc:
        return f"Write error: {exc}"


def _exec_list_directory(path: str) -> str:
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Path not found: {p}"
        if not p.is_dir():
            return f"Not a directory: {p}"
        entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        lines = [f"{'[DIR] ' if e.is_dir() else '[FILE]'} {e.name}" for e in entries]
        return "\n".join(lines) if lines else "(empty directory)"
    except Exception as exc:
        return f"List error: {exc}"


# Cross-platform uvx detection
_UVX_PATH_WIN = Path.home() / ".local" / "bin" / "uvx.exe"
_UVX_PATH_UNIX = Path.home() / ".local" / "bin" / "uvx"
_UVX_PATH = _UVX_PATH_WIN if _UVX_PATH_WIN.exists() else _UVX_PATH_UNIX


def _mcp_understand_image(image_source: str, prompt: str, api_key: str) -> str:
    """Call MiniMax MCP understand_image tool via JSON-RPC over stdio."""
    if not _UVX_PATH.exists():
        return "Error: uvx not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"

    env = os.environ.copy()
    env["MINIMAX_API_KEY"] = api_key
    env["MINIMAX_API_HOST"] = "https://api.minimax.io"

    try:
        proc = subprocess.Popen(
            [str(_UVX_PATH), "minimax-coding-plan-mcp"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, text=True,
        )

        def send_rpc(msg: dict) -> None:
            line = json.dumps(msg) + "\n"
            proc.stdin.write(line)
            proc.stdin.flush()

        def read_rpc() -> dict | None:
            while True:
                line = proc.stdout.readline()
                if not line:
                    return None
                line = line.strip()
                if not line:
                    continue
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

        # Initialize
        send_rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "bot-bridge", "version": "1.0"}
        }})
        init_resp = read_rpc()
        log(f"MCP init: {init_resp}")

        # Send initialized notification
        send_rpc({"jsonrpc": "2.0", "method": "notifications/initialized"})

        # Call understand_image
        send_rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
            "name": "understand_image",
            "arguments": {"prompt": prompt, "image_source": image_source}
        }})
        result = read_rpc()
        log(f"MCP understand_image result keys: {list(result.keys()) if isinstance(result, dict) else 'none'}")

        proc.stdin.close()
        proc.terminate()

        if isinstance(result, dict) and "result" in result:
            content = result["result"].get("content", [])
            texts = []
            for c in content:
                if c.get("type") == "text":
                    t = c.get("text", "")
                    # Fix double-encoded UTF-8 (mojibake from some MCP servers)
                    try:
                        t = t.encode("latin-1").decode("utf-8")
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        pass
                    texts.append(t)
            return "\n".join(texts) if texts else "No image analysis returned."
        return f"MCP returned unexpected format: {json.dumps(result)[:500]}"

    except Exception as exc:
        return f"MCP image error: {exc}"


def _exec_ask_claude(message: str) -> str:
    try:
        result = subprocess.run(
            ["claude", "-p", "--output-format", "json", message],
            capture_output=True, text=True, timeout=120,
        )
        combined = "\n".join([result.stdout or "", result.stderr or ""])
        for line in reversed(combined.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                try:
                    payload = json.loads(line)
                    reply = payload.get("result", "")
                    if isinstance(reply, str) and reply.strip():
                        return reply.strip()
                except json.JSONDecodeError:
                    continue
        return f"Claude did not return a usable response.\n{combined[-500:]}"
    except subprocess.TimeoutExpired:
        return "Claude timed out."
    except FileNotFoundError:
        return "Claude CLI not found in PATH."
    except Exception as exc:
        return f"ask_claude error: {exc}"


_SPOTIFY_SCRIPT = Path(__file__).resolve().parent.parent / "spotify-control" / "spotify_control.py"
_SPOTIFY_ENV_FILE = Path.home() / "bot.env"


def _exec_spotify(args: list[str]) -> str:
    if not _SPOTIFY_SCRIPT.exists():
        return "Error: spotify_control.py not found."
    env = os.environ.copy()
    env["SPOTIFY_ENV_FILE"] = str(_SPOTIFY_ENV_FILE)
    try:
        result = subprocess.run(
            [sys.executable, str(_SPOTIFY_SCRIPT)] + args,
            capture_output=True, text=True, timeout=20, env=env,
        )
        output = (result.stdout + result.stderr).strip()
        return output if output else "No output from Spotify."
    except subprocess.TimeoutExpired:
        return "Spotify command timed out."
    except Exception as exc:
        return f"Spotify error: {exc}"


def _dispatch_tool(name: str, tool_input: dict[str, Any]) -> str:
    if name == "web_search":
        return _exec_web_search(tool_input.get("query", ""))
    if name == "read_file":
        return _exec_read_file(tool_input.get("path", ""))
    if name == "write_file":
        return _exec_write_file(tool_input.get("path", ""), tool_input.get("content", ""))
    if name == "list_directory":
        return _exec_list_directory(tool_input.get("path", ""))
    if name == "spotify_play":
        args = ["play", tool_input.get("query", "")]
        device = tool_input.get("device")
        if device:
            args += ["--device", device]
        return _exec_spotify(args)
    if name == "spotify_devices":
        return _exec_spotify(["devices"])
    if name == "spotify_search":
        return _exec_spotify(["search", tool_input.get("query", "")])
    if name == "ask_claude":
        return _exec_ask_claude(tool_input.get("message", ""))
    return f"Unknown tool: {name}"

MAX_TELEGRAM_CHARS = 3900
MAX_SESSION_MESSAGES = 20


class BridgeError(RuntimeError):
    """Raised when the bridge cannot complete a provider or API call."""


def now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message: str) -> None:
    print(f"[{now_ts()}] {message}", flush=True)


def load_env_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"").strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def env_csv(name: str) -> list[str]:
    raw = os.getenv(name, "")
    if not raw.strip():
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def split_message(text: str, limit: int = MAX_TELEGRAM_CHARS) -> list[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return ["(empty response)"]
    if len(cleaned) <= limit:
        return [cleaned]

    chunks: list[str] = []
    cursor = cleaned
    while len(cursor) > limit:
        split_at = cursor.rfind("\n", 0, limit)
        if split_at < int(limit * 0.6):
            split_at = cursor.rfind(" ", 0, limit)
        if split_at < int(limit * 0.5):
            split_at = limit
        chunks.append(cursor[:split_at].strip())
        cursor = cursor[split_at:].strip()
    if cursor:
        chunks.append(cursor)
    return chunks


@dataclass
class BridgeConfig:
    env_file: Path
    state_file: Path
    poll_seconds: float
    telegram_poll_timeout: int
    telegram_token: str | None
    allowed_telegram_chat_ids: set[int]
    llm_base_url: str
    llm_api_key: str | None
    llm_model: str
    llm_system_prompt: str
    llm_timeout_seconds: float
    llm_format: str  # "openai" or "anthropic"


def default_state_file() -> Path:
    return Path(__file__).resolve().parent / "state" / "bot_bridge_state.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bot bridge for Telegram.")
    parser.add_argument("--env-file", default=os.getenv("BOT_ENV_FILE") or str(Path.home() / "bot.env"))
    parser.add_argument("--state-file", default=os.getenv("BOT_STATE_FILE") or str(default_state_file()))
    parser.add_argument("--poll-seconds", type=float, default=float(os.getenv("BOT_POLL_SECONDS", "2")))
    parser.add_argument(
        "--telegram-poll-timeout",
        type=int,
        default=int(os.getenv("BOT_TELEGRAM_POLL_TIMEOUT", "20")),
    )
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> BridgeConfig:
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    allowed_chat_ids: set[int] = set()
    for item in env_csv("BOT_ALLOWED_TELEGRAM_CHAT_IDS"):
        try:
            allowed_chat_ids.add(int(item))
        except ValueError:
            log(f"Ignoring invalid chat id in BOT_ALLOWED_TELEGRAM_CHAT_IDS: {item}")

    return BridgeConfig(
        env_file=Path(args.env_file).expanduser(),
        state_file=Path(args.state_file).expanduser(),
        poll_seconds=max(0.2, float(args.poll_seconds)),
        telegram_poll_timeout=max(1, int(args.telegram_poll_timeout)),
        telegram_token=token,
        allowed_telegram_chat_ids=allowed_chat_ids,
        llm_base_url=(os.getenv("BOT_LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/"),
        llm_api_key=os.getenv("BOT_LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
        llm_model=os.getenv("BOT_LLM_MODEL") or "gpt-4o-mini",
        llm_system_prompt=(
            os.getenv("BOT_LLM_SYSTEM_PROMPT")
            or "You are a concise helpful assistant responding in plain text."
        ),
        llm_timeout_seconds=max(5.0, float(os.getenv("BOT_LLM_TIMEOUT_SECONDS", "45"))),
        llm_format=(os.getenv("BOT_LLM_FORMAT") or "openai").lower().strip(),
    )


def load_state(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            state = {}
    else:
        state = {}

    if not isinstance(state, dict):
        state = {}

    if not isinstance(state.get("telegram_offset"), int):
        state["telegram_offset"] = 0
    if not isinstance(state.get("sessions"), dict):
        state["sessions"] = {}

    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, indent=2, ensure_ascii=True)
    path.write_text(payload + "\n", encoding="utf-8")


def _build_history(cfg: BridgeConfig, state: dict[str, Any], session_id: str, prompt: str) -> list[dict[str, str]]:
    sessions = state.setdefault("sessions", {})
    history = sessions.setdefault(session_id, [])
    if not isinstance(history, list):
        history = []
    history.append({"role": "user", "content": prompt})
    history = history[-MAX_SESSION_MESSAGES:]
    sessions[session_id] = history
    return history


def _llm_openai(cfg: BridgeConfig, history: list[dict[str, str]]) -> str:
    messages: list[dict[str, str]] = [{"role": "system", "content": cfg.llm_system_prompt}]
    for item in history:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str):
            messages.append({"role": role, "content": content})

    headers = {"Content-Type": "application/json"}
    if cfg.llm_api_key:
        headers["Authorization"] = f"Bearer {cfg.llm_api_key}"

    url = f"{cfg.llm_base_url}/chat/completions"
    try:
        response = requests.post(url, headers=headers, json={"model": cfg.llm_model, "messages": messages}, timeout=cfg.llm_timeout_seconds)
    except requests.RequestException as exc:
        raise BridgeError(f"LLM request failed: {exc}") from exc

    if response.status_code >= 400:
        body = response.text.strip()
        if len(body) > 500:
            body = body[:500] + "..."
        raise BridgeError(f"LLM HTTP {response.status_code}: {body}")

    try:
        data = response.json()
    except ValueError as exc:
        raise BridgeError("LLM response was not valid JSON") from exc

    reply = ""
    if isinstance(data, dict):
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            choice_0 = choices[0]
            if isinstance(choice_0, dict):
                message = choice_0.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        reply = content.strip()
    return reply


def _llm_anthropic(cfg: BridgeConfig, history: list[dict[str, str]]) -> str:
    if _anthropic_sdk is None:
        raise BridgeError("anthropic package is not installed. Run: pip install anthropic")

    msgs: list[Any] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str):
            msgs.append({"role": role, "content": content})

    client = _anthropic_sdk.Anthropic(base_url=cfg.llm_base_url, api_key=cfg.llm_api_key or "")

    for _ in range(_MAX_TOOL_TURNS):
        try:
            response = client.messages.create(
                model=cfg.llm_model,
                max_tokens=4096,
                system=cfg.llm_system_prompt,
                tools=_TOOL_DEFINITIONS,
                messages=msgs,
            )
        except Exception as exc:
            raise BridgeError(f"Anthropic LLM request failed: {exc}") from exc

        # Collect tool_use blocks and text blocks
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if hasattr(b, "text") and isinstance(b.text, str)]

        if not tool_uses or response.stop_reason == "end_turn":
            # Final answer
            return text_blocks[0].text.strip() if text_blocks else ""

        # Execute tools and feed results back
        log(f"Bot using tools: {[t.name for t in tool_uses]}")
        msgs.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tu in tool_uses:
            result = _dispatch_tool(tu.name, tu.input)
            log(f"Tool {tu.name} result length: {len(result)}")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": result,
            })
        msgs.append({"role": "user", "content": tool_results})

    return "Sorry, I could not complete the task in time."


def llm_chat_completion(cfg: BridgeConfig, state: dict[str, Any], session_id: str, prompt: str) -> str:
    history = _build_history(cfg, state, session_id, prompt)

    if cfg.llm_format == "anthropic":
        reply = _llm_anthropic(cfg, history)
    else:
        reply = _llm_openai(cfg, history)

    if not reply:
        reply = "I could not generate a response right now."

    sessions = state.setdefault("sessions", {})
    history.append({"role": "assistant", "content": reply})
    sessions[session_id] = history[-MAX_SESSION_MESSAGES:]
    return reply


def llm_chat_completion_with_image(cfg: BridgeConfig, state: dict[str, Any], session_id: str, caption: str, photo_data: dict) -> str:
    """Analyze image via MCP, then send description + caption to LLM for response."""
    log("Calling MCP understand_image...")
    image_description = _mcp_understand_image(photo_data["url"], caption, cfg.llm_api_key or "")
    log(f"MCP image result length: {len(image_description)}")

    if image_description.startswith("Error:") or image_description.startswith("MCP"):
        log(f"MCP failed: {image_description}")
        enriched_prompt = f"[The user sent an image but analysis failed. Caption: {caption}]"
    else:
        enriched_prompt = f"[The user sent an image. Image analysis: {image_description}] User message: {caption}"

    return llm_chat_completion(cfg, state, session_id, enriched_prompt)


def telegram_request(token: str, method: str, payload: dict[str, Any], timeout: float = 60.0) -> Any:
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        response = requests.post(url, data=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise BridgeError(f"Telegram request failed: {exc}") from exc

    if response.status_code >= 400:
        raise BridgeError(f"Telegram HTTP {response.status_code}: {response.text[:400]}")

    try:
        body = response.json()
    except ValueError as exc:
        raise BridgeError("Telegram response was not valid JSON") from exc

    if not isinstance(body, dict) or not body.get("ok"):
        raise BridgeError(f"Telegram API error: {body}")

    return body.get("result")


def telegram_send_message(token: str, chat_id: int, text: str, reply_to_message_id: int | None = None) -> None:
    for chunk in split_message(text):
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "Markdown",
        }
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        telegram_request(token, "sendMessage", payload, timeout=30)


def telegram_help_text() -> str:
    return (
        "Bot bridge commands:\n"
        "/help - Show this message\n"
        "/status - Show bot status\n"
        "/clear - Clear conversation history\n"
        "Any other message is sent to the configured LLM backend."
    )


def telegram_status_text(cfg: BridgeConfig) -> str:
    telegram_state = "enabled" if cfg.telegram_token else "disabled"
    return (
        f"telegram: {telegram_state}\n"
        f"llm_model: {cfg.llm_model}\n"
        f"llm_format: {cfg.llm_format}\n"
        f"llm_base_url: {cfg.llm_base_url}"
    )


def telegram_download_photo(token: str, photo_list: list[dict]) -> dict | None:
    """Download the largest photo from Telegram. Returns dict with b64, media_type, url, or None."""
    if not photo_list:
        return None
    best = photo_list[-1]  # largest size is last
    file_id = best.get("file_id")
    if not file_id:
        return None
    try:
        file_info = telegram_request(token, "getFile", {"file_id": file_id})
        if not isinstance(file_info, dict):
            return None
        file_path = file_info.get("file_path", "")
        url = f"https://api.telegram.org/file/bot{token}/{file_path}"
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return None
        b64 = base64.b64encode(resp.content).decode("ascii")
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "jpg"
        media_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}
        media_type = media_map.get(ext, "image/jpeg")
        return {"b64": b64, "media_type": media_type, "url": url}
    except Exception as exc:
        log(f"Photo download error: {exc}")
        return None


def handle_telegram_message(cfg: BridgeConfig, state: dict[str, Any], message: dict[str, Any]) -> bool:
    if not cfg.telegram_token:
        return False

    chat = message.get("chat")
    if not isinstance(chat, dict):
        return False
    chat_id = chat.get("id")
    if not isinstance(chat_id, int):
        return False

    if cfg.allowed_telegram_chat_ids and chat_id not in cfg.allowed_telegram_chat_ids:
        log(f"Skipping disallowed Telegram chat_id={chat_id}")
        return False

    message_id = message.get("message_id")
    reply_to_message_id = message_id if isinstance(message_id, int) else None
    session_id = f"telegram:{chat_id}"

    # Check for photo
    photo_list = message.get("photo")
    if isinstance(photo_list, list) and photo_list:
        caption = message.get("caption", "").strip() or "What do you see in this image?"
        photo_data = telegram_download_photo(cfg.telegram_token, photo_list)
        if photo_data:
            log(f"Photo received, size={len(photo_data['b64'])//1024}KB, caption='{caption}'")
            reply = llm_chat_completion_with_image(cfg, state, session_id, caption, photo_data)
            telegram_send_message(cfg.telegram_token, chat_id, reply, reply_to_message_id)
            return True

    text = message.get("text")
    if not isinstance(text, str) or not text.strip():
        return False

    text = text.strip()

    lower = text.lower()
    if lower in {"/start", "/help"}:
        telegram_send_message(cfg.telegram_token, chat_id, telegram_help_text(), reply_to_message_id)
        return False
    if lower == "/status":
        telegram_send_message(cfg.telegram_token, chat_id, telegram_status_text(cfg), reply_to_message_id)
        return False
    if lower == "/clear":
        sessions = state.setdefault("sessions", {})
        sessions[session_id] = []
        telegram_send_message(cfg.telegram_token, chat_id, "Session cleared. Starting fresh!", reply_to_message_id)
        return True

    reply = llm_chat_completion(cfg, state, session_id, text)
    telegram_send_message(cfg.telegram_token, chat_id, reply, reply_to_message_id)
    return True


def poll_telegram(cfg: BridgeConfig, state: dict[str, Any]) -> bool:
    if not cfg.telegram_token:
        return False

    timeout = cfg.telegram_poll_timeout

    payload = {
        "offset": state.get("telegram_offset", 0),
        "timeout": timeout,
        "allowed_updates": json.dumps(["message"]),
    }

    updates = telegram_request(cfg.telegram_token, "getUpdates", payload, timeout=float(timeout + 10))
    if not isinstance(updates, list):
        return False

    changed = False
    for update in updates:
        if not isinstance(update, dict):
            continue
        update_id = update.get("update_id")
        if isinstance(update_id, int):
            state["telegram_offset"] = max(state.get("telegram_offset", 0), update_id + 1)
            changed = True

        message = update.get("message")
        if isinstance(message, dict):
            changed = handle_telegram_message(cfg, state, message) or changed

    return changed


def validate_startup(cfg: BridgeConfig) -> tuple[bool, bool]:
    telegram_enabled = bool(cfg.telegram_token)

    if telegram_enabled and cfg.telegram_token:
        try:
            me = telegram_request(cfg.telegram_token, "getMe", {}, timeout=20)
            username = me.get("username") if isinstance(me, dict) else None
            if isinstance(username, str) and username:
                log(f"Telegram connected as @{username}")
            else:
                log("Telegram connected")
        except Exception as exc:  # noqa: BLE001
            log(f"Telegram disabled due to startup error: {exc}")
            telegram_enabled = False
    return telegram_enabled, False


def main() -> int:
    args = parse_args()
    env_file = Path(args.env_file).expanduser().resolve()
    load_env_file(env_file)

    cfg = build_config(args)
    cfg.state_file.parent.mkdir(parents=True, exist_ok=True)

    state = load_state(cfg.state_file)

    telegram_enabled, whatsapp_enabled = validate_startup(cfg)
    cfg.telegram_token = cfg.telegram_token if telegram_enabled else None

    if not cfg.telegram_token:
        print(
            "Telegram is not enabled. Configure TELEGRAM_BOT_TOKEN.",
            flush=True,
        )
        return 2

    log(f"State file: {cfg.state_file}")
    log(f"Env file: {cfg.env_file}")
    log(f"LLM model: {cfg.llm_model}")
    log(f"LLM format: {cfg.llm_format}")

    save_state(cfg.state_file, state)

    while True:
        changed = False

        if cfg.telegram_token:
            try:
                changed = poll_telegram(cfg, state) or changed
            except Exception as exc:  # noqa: BLE001
                log(f"Telegram poll error: {exc}")

        if changed:
            save_state(cfg.state_file, state)

        time.sleep(cfg.poll_seconds)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        log("bot_bridge interrupted, exiting")
        raise SystemExit(0)
