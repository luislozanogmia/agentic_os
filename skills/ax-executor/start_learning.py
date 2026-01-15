# .claude/skills/ax-executor/start_learning.py
"""
Start a symbolic learning session: launch mouse & keyboard trackers,
collect events to a session-specific log folder, and run until `stop_event`
is set (API-driven) or user interrupts (CLI).

This module is called by learning_api.start_session().
"""

from __future__ import annotations

import os
import time
import threading
from datetime import datetime
from typing import Optional

from mouse_tracker import run_mouse_tracker # type: ignore
from keyboard_tracker import run_keyboard_tracker # type: ignore

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
# Centralized location for all learning session logs
LOG_DIR = os.path.join(_THIS_DIR, "learning_logs")
os.makedirs(LOG_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Session runner
# ---------------------------------------------------------------------------
def start_learning_session(session_name: Optional[str] = None, stop_event=None):
    """
    Launch mouse + keyboard trackers in background threads and block until stop_event is set.

    Args:
        session_name: Optional string label. If None and running in CLI (__main__),
                      user will be prompted; otherwise auto-generated timestamp label used.
        stop_event: threading.Event supplied by caller (learning_api). If None, a local
                    Event is created and the session becomes self-owned (CLI mode).
    """
    cli_mode = __name__ == "__main__" and stop_event is None

    if stop_event is None:
        stop_event = threading.Event()

    # --- Resolve session name ------------------------------------------------
    if session_name is None:
        if cli_mode:
            try:
                session_name = input("...name of session? ").strip().replace(" ", "_")
            except EOFError:
                session_name = None
        if not session_name:
            session_name = f"ui_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    else:
        session_name = session_name.strip().replace(" ", "_")

    # --- Paths ---------------------------------------------------------------
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_folder = f"{session_name}_{timestamp}"
    SESSION_DIR = os.path.join(LOG_DIR, session_folder)
    SCREEN_DIR = os.path.join(SESSION_DIR, "screens")
    os.makedirs(SCREEN_DIR, exist_ok=True)

    LOG_PATH = os.path.join(SESSION_DIR, "learning_id.json")

    # active session pointer (optional convenience for other tools)
    with open(os.path.join(LOG_DIR, "active_log_path.tmp"), "w") as f:
        f.write(LOG_PATH)

    print(f"[+] Session log: {LOG_PATH}")

    # CLI countdown (skip when API-driven)
    if cli_mode:
        print("[*] Symbolic learning pulse active — press Ctrl+C to stop.\n")
        print("[⏳] Get ready! Starting in...")
        for i in range(3, 0, -1):
            print(f"[{i}] {i}...")
            time.sleep(1)
        print("[🚀] GO! Learning session active!")
    else:
        print("[🚀] Learning session active (API).")

    # --- Launch trackers -----------------------------------------------------
    mouse_thread = threading.Thread(
        target=run_mouse_tracker,
        args=(LOG_PATH, SCREEN_DIR, stop_event),
        daemon=True,
    )
    keyboard_thread = threading.Thread(
        target=run_keyboard_tracker,
        args=(LOG_PATH, stop_event),
        daemon=True,
    )
    mouse_thread.start()
    keyboard_thread.start()

    # --- Wait loop -----------------------------------------------------------
    try:
        while True:
            if stop_event.is_set():
                print("[🛑] Stop signal received - ending learning session")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        if cli_mode:
            confirm = input("\n[⚠️] Ctrl+C — stop session? (y/n): ").strip().lower()
            if confirm == "y":
                stop_event.set()
            else:
                print("[↩️] Resuming session...")

    # --- Shutdown ------------------------------------------------------------
    stop_event.set()  # idempotent
    print("[🛑] Waiting for background trackers...")
    if mouse_thread.is_alive():
        mouse_thread.join(timeout=2.0)
    if keyboard_thread.is_alive():
        keyboard_thread.join(timeout=2.0)
    print("[✅] Learning session completely stopped")


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    start_learning_session()
