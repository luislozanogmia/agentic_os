#!/usr/bin/env python3
"""
Minimal Floating Recording UI for AX Executor

A lightweight macOS floating window with Record/Stop buttons.
Click to control workflow recording without terminal disruption.

Usage:
    # From ~/.claude/skills/ax-executor/
    python3 recording_ui.py

    # Or from ~/.claude/
    python3 skills/ax-executor/recording_ui.py

    # Or with full path
    ~/.claude/.venv/bin/python3 ~/.claude/skills/ax-executor/recording_ui.py
"""

import sys
import json
import subprocess
import threading
import signal
from pathlib import Path

# Handle running from different directories
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    import objc
    from AppKit import (
        NSApplication, NSWindow, NSButton, NSTextField,
        NSView, NSRect, NSPoint, NSSize,
        NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
        NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
        NSBackingStoreBuffered, NSColor, NSFont,
        NSApplicationActivationPolicyAccessory,
        NSEventMaskLeftMouseDown, NSEventTypeLeftMouseDown,
        NSCompositingOperationSourceOver
    )
    from Foundation import NSObject, NSTimer
except ImportError as e:
    raise RuntimeError(
        "AppKit/Foundation import failed. Make sure PyObjC is installed:\n"
        "  pip install pyobjc pyobjc-framework-Cocoa\n"
        f"Error details: {e}"
    ) from e


class RecordingUIDelegate(NSObject):
    """Delegate for Recording UI window"""

    def __init__(self):
        objc.super(RecordingUIDelegate, self).__init__()
        self.recording = False
        self.workflow_name = "workflow"
        self.session_id = None
        self.ax_executor_path = Path(__file__).parent / "ax_executor_skill.py"

    def recordButtonClicked_(self, sender):
        """Start recording"""
        if self.recording:
            print("[⚠️] Already recording")
            return

        workflow_name = self.get_workflow_name()
        self.start_recording(workflow_name)
        self.recording = True
        sender.setEnabled_(False)
        self.stop_button.setEnabled_(True)
        self.status_label.setStringValue_("Status: Recording...")

    def stopButtonClicked_(self, sender):
        """Stop recording"""
        if not self.recording:
            print("[⚠️] Not recording")
            return

        self.stop_recording()
        self.recording = False
        sender.setEnabled_(False)
        self.record_button.setEnabled_(True)
        self.status_label.setStringValue_("Status: Ready")

    def get_workflow_name(self):
        """Get workflow name from user or use default"""
        # For now, use timestamp-based name
        from datetime import datetime
        return f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def start_recording(self, workflow_name):
        """Start recording session in background"""
        def run_record():
            try:
                cmd = [
                    sys.executable,
                    str(self.ax_executor_path),
                    "--record",
                    workflow_name
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"[🎬] Recording started: {workflow_name}")
                    self.session_id = workflow_name
                else:
                    print(f"[❌] Recording failed: {result.stderr}")
            except Exception as e:
                print(f"[❌] Error starting recording: {e}")

        thread = threading.Thread(target=run_record, daemon=True)
        thread.start()

    def stop_recording(self):
        """Stop recording session in background"""
        def run_stop():
            try:
                cmd = [sys.executable, str(self.ax_executor_path), "--stop-record"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"[✅] Recording stopped")
                    self.session_id = None
                else:
                    print(f"[❌] Stop failed: {result.stderr}")
            except Exception as e:
                print(f"[❌] Error stopping recording: {e}")

        thread = threading.Thread(target=run_stop, daemon=True)
        thread.start()


def create_recording_ui():
    """Create and show floating recording UI"""
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    # Handle Ctrl+C gracefully
    def signal_handler(signum, frame):
        print("\n[🛑] Ctrl+C detected - shutting down")
        app.terminate_(None)

    signal.signal(signal.SIGINT, signal_handler)

    # Create window
    window_rect = NSRect((100, 100), (280, 120))
    window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        window_rect,
        NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable,
        NSBackingStoreBuffered,
        False
    )

    window.setTitle_("AX Recording Control")
    window.setLevel_(3)  # Floating window level
    window.setOpaque_(False)
    window.setBackgroundColor_(NSColor.windowBackgroundColor())

    # Create delegate
    delegate = RecordingUIDelegate.alloc().init()
    window.setDelegate_(delegate)

    # Create content view
    content_view = NSView.alloc().initWithFrame_(
        NSRect((0, 0), (280, 120))
    )
    window.setContentView_(content_view)

    # Status label
    status_label = NSTextField.alloc().initWithFrame_(
        NSRect((10, 85), (260, 20))
    )
    status_label.setStringValue_("Status: Ready")
    status_label.setFont_(NSFont.systemFontOfSize_(12))
    status_label.setEditable_(False)
    content_view.addSubview_(status_label)

    # Record button
    record_button = NSButton.alloc().initWithFrame_(
        NSRect((10, 45), (130, 30))
    )
    record_button.setTitle_("🎬 Record")
    record_button.setBezelStyle_(4)  # Rounded button
    record_button.setTarget_(delegate)
    record_button.setAction_("recordButtonClicked:")
    content_view.addSubview_(record_button)

    # Stop button
    stop_button = NSButton.alloc().initWithFrame_(
        NSRect((150, 45), (120, 30))
    )
    stop_button.setTitle_("⏹ Stop")
    stop_button.setBezelStyle_(4)
    stop_button.setTarget_(delegate)
    stop_button.setAction_("stopButtonClicked:")
    stop_button.setEnabled_(False)
    content_view.addSubview_(stop_button)

    # Info label
    info_label = NSTextField.alloc().initWithFrame_(
        NSRect((10, 10), (260, 25))
    )
    info_label.setStringValue_("Recording session active\nExecute your workflow")
    info_label.setFont_(NSFont.systemFontOfSize_(10))
    info_label.setEditable_(False)
    content_view.addSubview_(info_label)

    # Store UI references in delegate for button methods to use
    delegate.status_label = status_label
    delegate.record_button = record_button
    delegate.stop_button = stop_button

    # Show window
    window.makeKeyAndOrderFront_(None)

    print("[✅] Floating Recording UI started")
    print("[💡] Click Record to start, Stop to finalize")
    print("[💡] Press Ctrl+C to quit")

    # AppKit must run on main thread, but we want Ctrl+C to work
    # Set up signal handler that will terminate the app
    def signal_handler(signum, frame):
        print("\n[🛑] Shutting down...")
        app.terminate_(None)

    signal.signal(signal.SIGINT, signal_handler)

    # Run app on main thread (required by AppKit)
    app.run()


if __name__ == "__main__":
    create_recording_ui()
