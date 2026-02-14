#!/usr/bin/env python3
"""Minimal macOS status bar controller for bot_bridge.py."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path

import objc
from AppKit import (
    NSAlert,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSMenu,
    NSMenuItem,
    NSObject,
    NSStatusBar,
)
from Foundation import NSTimer

try:
    from PyObjCTools import AppHelper
except ImportError:
    AppHelper = None

ROOT_DIR = Path(__file__).resolve().parent
RUNNER = ROOT_DIR / "run_bot_bridge.sh"
BRIDGE_SCRIPT = ROOT_DIR / "bot_bridge.py"
LOG_FILE = ROOT_DIR / "logs" / "bot_bridge.log"
STATE_DIR = ROOT_DIR / "state"
ENV_FILE = Path(os.getenv("BOT_ENV_FILE") or Path.home() / "bot.env")


def now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message: str) -> None:
    print(f"[{now_ts()}] {message}", flush=True)


def alert(title: str, message: str) -> None:
    popup = NSAlert.alloc().init()
    popup.setMessageText_(title)
    popup.setInformativeText_(message)
    popup.addButtonWithTitle_("OK")
    popup.runModal()


def read_last_lines(path: Path, n: int = 10) -> str:
    if not path.exists():
        return "(no log yet)"
    try:
        lines = path.read_text(errors="replace").splitlines()
    except Exception:
        return "(unable to read log)"
    if not lines:
        return "(empty log)"
    return "\n".join(lines[-n:])


def running_bridge_pids() -> list[int]:
    result = subprocess.run(
        ["ps", "-ax", "-o", "pid=,command="],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    target = str(BRIDGE_SCRIPT)
    pids: list[int] = []
    for raw_line in (result.stdout or "").splitlines():
        line = raw_line.strip()
        if not line or target not in line:
            continue
        pid_str = line.split(None, 1)[0]
        try:
            pids.append(int(pid_str))
        except ValueError:
            continue
    return sorted(set(pids))


def is_bridge_running() -> bool:
    return bool(running_bridge_pids())


def kill_bridge(timeout_seconds: float = 4.0) -> bool:
    pids = running_bridge_pids()
    if not pids:
        return True

    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not running_bridge_pids():
            return True
        time.sleep(0.2)

    for pid in running_bridge_pids():
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            continue

    time.sleep(0.2)
    return not running_bridge_pids()


class AppDelegate(NSObject):
    def init(self):
        self = objc.super(AppDelegate, self).init()
        if self is None:
            return None
        self.status_item = None
        self.running_state = None
        return self

    def applicationDidFinishLaunching_(self, notification):
        self._create_status_item()
        self._refresh_state()
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            2.0,
            self,
            "refreshTimerTick:",
            None,
            True,
        )
        log("bot bar started")

    def _create_status_item(self):
        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1)
        button = self.status_item.button()
        if button:
            button.setTitle_("bot: OFF")

        menu = NSMenu.alloc().init()
        menu.setAutoenablesItems_(False)
        self.start_item = self._menu_item("Start Bot", "startBridge:")
        self.stop_item = self._menu_item("Stop Bot", "stopBridge:")
        self.restart_item = self._menu_item("Restart Bot", "restartBridge:")
        self.status_item_menu = self._menu_item("Show Status", "showStatus:")
        self.open_log_item = self._menu_item("Open Log", "openLog:")
        self.open_env_item = self._menu_item("Open bot.env", "openEnv:")
        self.open_state_item = self._menu_item("Open State Folder", "openState:")
        self.quit_item = self._menu_item("Quit", "quitApp:")

        menu.addItem_(self.start_item)
        menu.addItem_(self.stop_item)
        menu.addItem_(self.restart_item)
        menu.addItem_(NSMenuItem.separatorItem())
        menu.addItem_(self.status_item_menu)
        menu.addItem_(self.open_log_item)
        menu.addItem_(self.open_env_item)
        menu.addItem_(self.open_state_item)
        menu.addItem_(NSMenuItem.separatorItem())
        menu.addItem_(self.quit_item)
        self.status_item.setMenu_(menu)

    def _menu_item(self, title: str, action: str):
        return NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, "")

    def _set_button_title(self, title: str):
        if not self.status_item:
            return
        button = self.status_item.button()
        if button:
            button.setTitle_(title)

    def _refresh_state(self):
        running = is_bridge_running()
        if running:
            self._set_button_title("bot: ON")
            self.start_item.setEnabled_(False)
            self.stop_item.setEnabled_(True)
            self.restart_item.setEnabled_(True)
        else:
            self._set_button_title("bot: OFF")
            self.start_item.setEnabled_(True)
            self.stop_item.setEnabled_(False)
            self.restart_item.setEnabled_(False)
        if self.running_state is None or self.running_state != running:
            state_text = "running" if running else "stopped"
            log(f"bot state changed: {state_text}")
        self.running_state = running

    def _start_bridge_process(self) -> tuple[bool, str]:
        if not RUNNER.exists():
            return False, f"Runner not found: {RUNNER}"
        if is_bridge_running():
            return True, "Bot bridge already running."

        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        proc = subprocess.Popen(
            ["/bin/bash", str(RUNNER)],
            cwd=str(ROOT_DIR),
            start_new_session=True,
        )
        time.sleep(1.0)
        if proc.poll() is not None:
            tail = read_last_lines(LOG_FILE, n=12)
            return False, f"Bot bridge exited early.\n\n{tail}"
        return True, "Bot bridge started."

    def _stop_bridge_process(self) -> tuple[bool, str]:
        if not is_bridge_running():
            return True, "Bot bridge is not running."
        ok = kill_bridge()
        if ok:
            return True, "Bot bridge stopped."
        tail = read_last_lines(LOG_FILE, n=12)
        return False, f"Failed to stop bot bridge.\n\n{tail}"

    def refreshTimerTick_(self, timer):
        self._refresh_state()

    def startBridge_(self, sender):
        ok, message = self._start_bridge_process()
        self._refresh_state()
        if ok:
            log(message)
        else:
            log(message)
            alert("Start failed", message)

    def stopBridge_(self, sender):
        ok, message = self._stop_bridge_process()
        self._refresh_state()
        if ok:
            log(message)
        else:
            log(message)
            alert("Stop failed", message)

    def restartBridge_(self, sender):
        ok_stop, stop_message = self._stop_bridge_process()
        if not ok_stop:
            self._refresh_state()
            log(stop_message)
            alert("Restart failed", stop_message)
            return

        ok_start, start_message = self._start_bridge_process()
        self._refresh_state()
        if ok_start:
            log(start_message)
        else:
            log(start_message)
            alert("Restart failed", start_message)

    def showStatus_(self, sender):
        pids = running_bridge_pids()
        pid_text = ", ".join(str(pid) for pid in pids) if pids else "none"
        message = (
            f"bridge_running: {'yes' if bool(pids) else 'no'}\n"
            f"bridge_pids: {pid_text}\n"
            f"env_file: {ENV_FILE}\n"
            f"log_file: {LOG_FILE}"
        )
        alert("Bot Bridge Status", message)

    def openLog_(self, sender):
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.touch(exist_ok=True)
        subprocess.run(["open", str(LOG_FILE)], check=False)

    def openEnv_(self, sender):
        if not ENV_FILE.exists():
            ENV_FILE.write_text("", encoding="utf-8")
        subprocess.run(["open", str(ENV_FILE)], check=False)

    def openState_(self, sender):
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(STATE_DIR)], check=False)

    def quitApp_(self, sender):
        log("bot bar exiting")
        if self.status_item:
            NSStatusBar.systemStatusBar().removeStatusItem_(self.status_item)
        NSApplication.sharedApplication().terminate_(None)


def main() -> int:
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    if AppHelper is not None:
        AppHelper.runEventLoop()
    else:
        log("PyObjCTools missing, using NSApplication.run fallback")
        app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
