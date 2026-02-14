#!/usr/bin/env python3
"""Multi-channel bot bridge for Telegram and WhatsApp with a generic LLM backend."""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

MAX_TELEGRAM_CHARS = 3900
MAX_SESSION_MESSAGES = 20
MAX_SEEN_WHATSAPP_IDS = 5000


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


def normalize_whatsapp_address(value: str) -> str:
    return (value or "").strip().lower()


@dataclass
class BridgeConfig:
    env_file: Path
    state_file: Path
    poll_seconds: float
    telegram_poll_timeout: int
    telegram_token: str | None
    allowed_telegram_chat_ids: set[int]
    whatsapp_enabled: bool
    twilio_account_sid: str | None
    twilio_auth_token: str | None
    twilio_from_number: str | None
    allowed_whatsapp_senders: set[str]
    llm_base_url: str
    llm_api_key: str | None
    llm_model: str
    llm_system_prompt: str
    llm_timeout_seconds: float


def default_state_file() -> Path:
    return Path(__file__).resolve().parent / "state" / "bot_bridge_state.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bot bridge for Telegram and WhatsApp.")
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
    token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("MIA_BRIDGE_BOT_KEY")
    if token and not os.getenv("TELEGRAM_BOT_TOKEN"):
        os.environ["TELEGRAM_BOT_TOKEN"] = token

    allowed_chat_ids: set[int] = set()
    for item in env_csv("BOT_ALLOWED_TELEGRAM_CHAT_IDS"):
        try:
            allowed_chat_ids.add(int(item))
        except ValueError:
            log(f"Ignoring invalid chat id in BOT_ALLOWED_TELEGRAM_CHAT_IDS: {item}")

    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from = os.getenv("TWILIO_WHATSAPP_NUMBER")
    whatsapp_default = bool(twilio_sid and twilio_token and twilio_from)
    whatsapp_enabled = env_bool("BOT_WHATSAPP_ENABLED", default=whatsapp_default)

    allowed_senders = {
        normalize_whatsapp_address(item)
        for item in env_csv("BOT_ALLOWED_WHATSAPP_SENDERS")
        if normalize_whatsapp_address(item)
    }

    return BridgeConfig(
        env_file=Path(args.env_file).expanduser(),
        state_file=Path(args.state_file).expanduser(),
        poll_seconds=max(0.2, float(args.poll_seconds)),
        telegram_poll_timeout=max(1, int(args.telegram_poll_timeout)),
        telegram_token=token,
        allowed_telegram_chat_ids=allowed_chat_ids,
        whatsapp_enabled=whatsapp_enabled,
        twilio_account_sid=twilio_sid,
        twilio_auth_token=twilio_token,
        twilio_from_number=twilio_from,
        allowed_whatsapp_senders=allowed_senders,
        llm_base_url=(os.getenv("BOT_LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/"),
        llm_api_key=os.getenv("BOT_LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
        llm_model=os.getenv("BOT_LLM_MODEL") or "gpt-4o-mini",
        llm_system_prompt=(
            os.getenv("BOT_LLM_SYSTEM_PROMPT")
            or "You are a concise helpful assistant responding in plain text."
        ),
        llm_timeout_seconds=max(5.0, float(os.getenv("BOT_LLM_TIMEOUT_SECONDS", "45"))),
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
    if not isinstance(state.get("whatsapp_seen_sids"), list):
        state["whatsapp_seen_sids"] = []

    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, indent=2, ensure_ascii=True)
    path.write_text(payload + "\n", encoding="utf-8")


def llm_chat_completion(cfg: BridgeConfig, state: dict[str, Any], session_id: str, prompt: str) -> str:
    sessions = state.setdefault("sessions", {})
    history = sessions.setdefault(session_id, [])
    if not isinstance(history, list):
        history = []

    history.append({"role": "user", "content": prompt})
    history = history[-MAX_SESSION_MESSAGES:]

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

    payload = {
        "model": cfg.llm_model,
        "messages": messages,
    }

    url = f"{cfg.llm_base_url}/chat/completions"
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=cfg.llm_timeout_seconds,
        )
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

    if not reply:
        reply = "I could not generate a response right now."

    history.append({"role": "assistant", "content": reply})
    sessions[session_id] = history[-MAX_SESSION_MESSAGES:]
    return reply


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
        }
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        telegram_request(token, "sendMessage", payload, timeout=30)


def telegram_help_text() -> str:
    return (
        "Bot bridge commands:\n"
        "/help\n"
        "/status\n"
        "Any other message is sent to the configured LLM backend."
    )


def telegram_status_text(cfg: BridgeConfig) -> str:
    telegram_state = "enabled" if cfg.telegram_token else "disabled"
    whatsapp_state = "enabled" if cfg.whatsapp_enabled else "disabled"
    return (
        f"telegram: {telegram_state}\n"
        f"whatsapp: {whatsapp_state}\n"
        f"llm_model: {cfg.llm_model}\n"
        f"llm_base_url: {cfg.llm_base_url}"
    )


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

    text = message.get("text")
    if not isinstance(text, str) or not text.strip():
        return False

    text = text.strip()
    message_id = message.get("message_id")
    reply_to_message_id = message_id if isinstance(message_id, int) else None

    lower = text.lower()
    if lower in {"/start", "/help"}:
        telegram_send_message(cfg.telegram_token, chat_id, telegram_help_text(), reply_to_message_id)
        return False
    if lower == "/status":
        telegram_send_message(cfg.telegram_token, chat_id, telegram_status_text(cfg), reply_to_message_id)
        return False

    session_id = f"telegram:{chat_id}"
    reply = llm_chat_completion(cfg, state, session_id, text)
    telegram_send_message(cfg.telegram_token, chat_id, reply, reply_to_message_id)
    return True


def poll_telegram(cfg: BridgeConfig, state: dict[str, Any]) -> bool:
    if not cfg.telegram_token:
        return False

    timeout = cfg.telegram_poll_timeout
    if cfg.whatsapp_enabled:
        timeout = min(timeout, 6)

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


def twilio_request(
    method: str,
    url: str,
    account_sid: str,
    auth_token: str,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    try:
        response = requests.request(
            method=method,
            url=url,
            auth=(account_sid, auth_token),
            params=params,
            data=data,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise BridgeError(f"Twilio request failed: {exc}") from exc

    if response.status_code >= 400:
        raise BridgeError(f"Twilio HTTP {response.status_code}: {response.text[:400]}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise BridgeError("Twilio response was not valid JSON") from exc

    if not isinstance(payload, dict):
        raise BridgeError("Twilio response shape was invalid")
    return payload


def twilio_send_whatsapp_message(cfg: BridgeConfig, to_number: str, text: str) -> None:
    if not (cfg.twilio_account_sid and cfg.twilio_auth_token and cfg.twilio_from_number):
        raise BridgeError("Twilio WhatsApp settings are incomplete")

    url = f"https://api.twilio.com/2010-04-01/Accounts/{cfg.twilio_account_sid}/Messages.json"
    payload = {
        "To": to_number,
        "From": cfg.twilio_from_number,
        "Body": text,
    }
    twilio_request(
        method="POST",
        url=url,
        account_sid=cfg.twilio_account_sid,
        auth_token=cfg.twilio_auth_token,
        data=payload,
        timeout=30.0,
    )


def poll_whatsapp(cfg: BridgeConfig, state: dict[str, Any]) -> bool:
    if not cfg.whatsapp_enabled:
        return False

    if not (cfg.twilio_account_sid and cfg.twilio_auth_token and cfg.twilio_from_number):
        raise BridgeError("BOT_WHATSAPP_ENABLED is true but Twilio credentials are missing")

    url = f"https://api.twilio.com/2010-04-01/Accounts/{cfg.twilio_account_sid}/Messages.json"
    payload = twilio_request(
        method="GET",
        url=url,
        account_sid=cfg.twilio_account_sid,
        auth_token=cfg.twilio_auth_token,
        params={"PageSize": "30"},
        timeout=30.0,
    )

    messages = payload.get("messages")
    if not isinstance(messages, list):
        return False

    seen_sids = state.get("whatsapp_seen_sids")
    if not isinstance(seen_sids, list):
        seen_sids = []
        state["whatsapp_seen_sids"] = seen_sids

    seen_lookup = {str(item) for item in seen_sids if isinstance(item, str)}
    own_number = normalize_whatsapp_address(cfg.twilio_from_number)

    changed = False

    for msg in reversed(messages):
        if not isinstance(msg, dict):
            continue

        sid = msg.get("sid")
        if not isinstance(sid, str) or not sid:
            continue

        if sid in seen_lookup:
            continue

        direction = (msg.get("direction") or "").strip().lower()
        if not direction.startswith("inbound"):
            continue

        from_number = normalize_whatsapp_address(str(msg.get("from") or ""))
        to_number = normalize_whatsapp_address(str(msg.get("to") or ""))

        if own_number and to_number and own_number != to_number:
            continue

        if cfg.allowed_whatsapp_senders and from_number not in cfg.allowed_whatsapp_senders:
            log(f"Skipping disallowed WhatsApp sender={from_number}")
            seen_sids.append(sid)
            seen_lookup.add(sid)
            changed = True
            continue

        body = str(msg.get("body") or "").strip()
        if not body:
            seen_sids.append(sid)
            seen_lookup.add(sid)
            changed = True
            continue

        session_id = f"whatsapp:{from_number}"
        reply = llm_chat_completion(cfg, state, session_id, body)
        twilio_send_whatsapp_message(cfg, str(msg.get("from")), reply)

        seen_sids.append(sid)
        seen_lookup.add(sid)
        changed = True

    if len(seen_sids) > MAX_SEEN_WHATSAPP_IDS:
        state["whatsapp_seen_sids"] = seen_sids[-MAX_SEEN_WHATSAPP_IDS:]

    return changed


def validate_startup(cfg: BridgeConfig) -> tuple[bool, bool]:
    telegram_enabled = bool(cfg.telegram_token)
    whatsapp_enabled = bool(cfg.whatsapp_enabled)

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

    if whatsapp_enabled:
        if not (cfg.twilio_account_sid and cfg.twilio_auth_token and cfg.twilio_from_number):
            log("WhatsApp disabled because Twilio settings are incomplete")
            whatsapp_enabled = False
        else:
            log("WhatsApp (Twilio) enabled")

    return telegram_enabled, whatsapp_enabled


def main() -> int:
    args = parse_args()
    env_file = Path(args.env_file).expanduser().resolve()
    load_env_file(env_file)

    cfg = build_config(args)
    cfg.state_file.parent.mkdir(parents=True, exist_ok=True)

    state = load_state(cfg.state_file)

    telegram_enabled, whatsapp_enabled = validate_startup(cfg)
    cfg.telegram_token = cfg.telegram_token if telegram_enabled else None
    cfg.whatsapp_enabled = whatsapp_enabled

    if not cfg.telegram_token and not cfg.whatsapp_enabled:
        print(
            "No channel enabled. Configure TELEGRAM_BOT_TOKEN/MIA_BRIDGE_BOT_KEY and/or Twilio WhatsApp keys.",
            flush=True,
        )
        return 2

    log(f"State file: {cfg.state_file}")
    log(f"Env file: {cfg.env_file}")
    log(f"LLM model: {cfg.llm_model}")

    save_state(cfg.state_file, state)

    while True:
        changed = False

        if cfg.telegram_token:
            try:
                changed = poll_telegram(cfg, state) or changed
            except Exception as exc:  # noqa: BLE001
                log(f"Telegram poll error: {exc}")

        if cfg.whatsapp_enabled:
            try:
                changed = poll_whatsapp(cfg, state) or changed
            except Exception as exc:  # noqa: BLE001
                log(f"WhatsApp poll error: {exc}")

        if changed:
            save_state(cfg.state_file, state)

        time.sleep(cfg.poll_seconds)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        log("bot_bridge interrupted, exiting")
        raise SystemExit(0)
