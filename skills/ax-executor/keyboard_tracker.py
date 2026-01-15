import os
import time
import threading
from datetime import datetime
from pynput import keyboard
import pyautogui
from log_writer import set_log_path, append_to_log
from text_cleaning import fix_simple_typos 
from system_info import enrich_keyboard_event, get_timestamp

try:
    import pygetwindow as gw
except ImportError:
    gw = None

# === Globals ===
text_buffer = ""
last_input_time = time.time()
buffer_lock = threading.Lock()
FLUSH_TIMEOUT = 1.5  # seconds
pressed_keys = set()
app_switch_sequence = []

# === Window Info ===
def get_active_window_info():
    if gw:
        try:
            win = gw.getActiveWindow()
            return {
                "title": win.title,
                "left": win.left,
                "top": win.top,
                "width": win.width,
                "height": win.height
            }
        except Exception:
            pass
    return {
        "title": "Unknown",
        "left": 0,
        "top": 0,
        "width": 1,
        "height": 1
    }

# === Flush typed buffer ===
def flush_buffer(trigger="timeout"):
    global text_buffer
    with buffer_lock:
        if text_buffer.strip():
            # Apply typo correction
            original_text = text_buffer.strip()
            corrected_text = fix_simple_typos(original_text)

            # Create raw keyboard event
            raw_event = {
                "event": "type",
                "text": corrected_text,
                "original": original_text,
                "input_timestamp": get_timestamp(),
                "trigger": trigger
            }

            # Enrich with app context using clean API
            enriched_event = enrich_keyboard_event(raw_event)
            if enriched_event is None:
                return  # Skip logging MIA Beta control events
            append_to_log(enriched_event)
            
            print(f"[✏️] Flushed buffer: '{original_text}' → '{corrected_text}' ({trigger})")
            text_buffer = ""

# === Timeout auto-flush ===
def timeout_checker():
    global last_input_time, _timeout_stop_event
    while True:
        # Check if we should stop
        if _timeout_stop_event and _timeout_stop_event.is_set():
            print("[🛑] Timeout checker stopping...")
            break
            
        time.sleep(0.5)
        if time.time() - last_input_time > FLUSH_TIMEOUT:
            flush_buffer(trigger="timeout")
            last_input_time = time.time()

# === Key press handler ===
def on_press(key):
    global text_buffer, last_input_time
    now = time.time()
    last_input_time = now

    print(f"[🧠] Key pressed: {key}")
    pressed_keys.add(key)

    # Enhanced app resolution console logging
    try:
        import subprocess
        frontmost_app = subprocess.check_output(
            ["osascript", "-e", 'tell application "System Events" to get name of first application process whose frontmost is true']
        ).decode().strip()
        main_pid = subprocess.check_output(["pgrep", "-ix", frontmost_app]).decode().strip().split("\n")[0]
        full_path = subprocess.check_output(["ps", "-p", main_pid, "-o", "args="]).decode().strip()

        print(f"[🧠] Frontmost App: {frontmost_app} — PID: {main_pid}")
        print(f"[🧠] App path: {full_path}")
    except Exception as err:
        print(f"[⚠️] Enhanced app resolution failed: {err}")

    if key == keyboard.Key.cmd:
        print("[🧷] Cmd key pressed (manual add)")

    try:
        # Detect cmd+tab for app switching
        if key == keyboard.Key.tab:
            if keyboard.Key.cmd in pressed_keys:
                # ADDED: Flush before app switch
                flush_buffer(trigger="app_switch")
                
                # Create raw switch app event
                raw_event = {
                    "event": "switch_app",
                    "key": "cmd+tab",
                    "input_timestamp": get_timestamp(),
                    "trigger": "switch"
                }
                
                # Enrich with app context using clean API
                enriched_event = enrich_keyboard_event(raw_event)
                if enriched_event is None:
                    return  # Skip logging MIA Beta control events
                append_to_log(enriched_event)
                print(f"[🔀] Detected app switch via cmd+tab")
                return
            else:
                print(f"[🔁] Tab pressed but modifier not detected: {pressed_keys}")

        key_str = str(key).lower().replace("'", "")
        if hasattr(key, 'char') and key.char:
            with buffer_lock:
                text_buffer += key.char

        else:
            if "space" in key_str:
                with buffer_lock:
                    text_buffer += ' '
                return

            elif any(k in key_str for k in ["enter", "tab", "esc", "f4"]):
                flush_buffer(trigger=key_str)
                
                # Create raw special key event
                raw_event = {
                    "event": "key",
                    "key": key_str,
                    "input_timestamp": get_timestamp(),
                    "trigger": "special"
                }
                
                # Enrich with app context using clean API
                enriched_event = enrich_keyboard_event(raw_event)
                if enriched_event is None:
                    return  # Skip logging MIA Beta control events
                append_to_log(enriched_event)
                print(f"[⌨️] Logged special key: {key_str}")

    except Exception as e:
        print(f"[⚠️] Key error: {e}")

# === Key release handler ===
def on_release(key):
    if key in pressed_keys:
        pressed_keys.remove(key)

# === Main Tracker ===
def run_keyboard_tracker(log_path=None, stop_event=None):
    global _timeout_stop_event
    _timeout_stop_event = stop_event
    if log_path is None:
        # Get the absolute path of this script (should be in mia_desktop/learning/)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        LOG_DIR = os.path.join(script_dir, "learning_logs")
        os.makedirs(LOG_DIR, exist_ok=True)
        log_path = os.path.join(LOG_DIR, "input_timestamp.json")

    set_log_path(log_path)

    print(f"[🧠] Keyboard tracker started — logging to {log_path}")
    threading.Thread(target=timeout_checker, daemon=True).start()
    
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    
    # Check for stop signal
    try:
        while True:
            if stop_event and stop_event.is_set():
                print("[🛑] Keyboard tracker stopping...")
                break
            time.sleep(0.1)
    finally:
        listener.stop()

# === CLI Entry ===
if __name__ == "__main__":
    run_keyboard_tracker()