# .claude/skills/ax_executor/log_writer.py
"""
Thread-safe JSON log writer for learning sessions
Essential for recording user actions during Teach Mode
"""
import os
import json
import threading
from pathlib import Path

write_lock = threading.Lock()
LOG_PATH = None

def set_log_path(path: str):
    """Set the log file path and ensure directory exists"""
    global LOG_PATH
    LOG_PATH = path
    
    # Ensure parent directory exists
    try:
        parent_dir = Path(path).parent
        parent_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[⚠️] Could not create log directory: {e}")

def append_to_log(event: dict):
    """Thread-safe append event to JSON log"""
    global LOG_PATH
    
    if LOG_PATH is None:
        raise ValueError("LOG_PATH not set. Call set_log_path(path) first.")

    with write_lock:
        log_data = []
        
        # Load existing log data
        if os.path.exists(LOG_PATH):
            try:
                with open(LOG_PATH, "r") as f:
                    content =f.read().strip()
                    if content:
                        log_data = json.loads(content)  # ← Use json.loads() with content string
                        print(f"[📖] Loaded {len(log_data)} existing events")
                    else:
                        print(f"[📝] Starting new log file")
            except json.JSONDecodeError as e:
                print(f"[⚠️] Log file corrupted, starting fresh: {e}")
                log_data = []
            except Exception as e:
                print(f"[⚠️] Could not load log file: {e}")
                log_data = []

        # Add new event
        log_data.append(event)
        print(f"[✅] Added event, total: {len(log_data)} events")

        # Write back to file
        try:
            with open(LOG_PATH, "w") as f:
                json.dump(log_data, f, indent=2)
            print(f"[💾] Successfully wrote {len(log_data)} events to log")
        except Exception as e:
            print(f"[❌] Failed to write to log file {LOG_PATH}: {e}")
            raise

def get_log_data() -> list:
    """Get current log data (useful for debugging)"""
    global LOG_PATH 
    
    if LOG_PATH is None or not os.path.exists(LOG_PATH):
        return []
    P
    try:
        with open(LOG_PATH, "r") as f:
            content = f.read().strip()
            if content:
                return json.load(f)
            return []
    except Exception as e:
        print(f"[⚠️] Could not read log data: {e}")
        return []

def clear_log():
    """Clear current log (useful for testing)"""
    global LOG_PATH
    
    if LOG_PATH and os.path.exists(LOG_PATH):
        try:
            with write_lock:
                with open(LOG_PATH, "w") as f:
                    json.dump([], f)
        except Exception as e:
            print(f"[⚠️] Could not clear log: {e}")