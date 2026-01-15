# .claude/skills/ax_executor/learning_api.py
"""
Clean Learning API - Session Management Only
Handles learning session control and status for beta
"""

# Skill-local version (FastAPI removed for standalone use)
from start_learning import start_learning_session
import threading
import os
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
# from cleaning import (  # Optional: comment out if not available
#     parse_event_timestamp,
#     clean_event_description,
#     normalize_timestamp
# )

# Consolidated base path for skill directory
BASE_DIR = Path(__file__).resolve().parent
LEARNING_LOGS_DIR = BASE_DIR / "learning_logs"

# ===== GLOBAL SESSION MANAGEMENT =====
learning_stop_event = threading.Event()
learning_active = False
_current_session_id: Optional[str] = None
_current_label: Optional[str] = None
_started_ts: Optional[float] = None
CURRENT_MODE: str = "idle"  # "idle" | "teach" | "auto"

# ===== MODE MANAGEMENT =====
def set_mode(mode: str):
    global CURRENT_MODE
    CURRENT_MODE = mode

def get_current_session_id() -> Optional[str]:
    """Get current session ID"""
    return _current_session_id

# ===== SESSION LIFECYCLE FUNCTIONS =====
def start_session(label: str = "session") -> str:
    """Start learning session - required by bridge.py"""
    global _current_session_id, _current_label, _started_ts, learning_active
    _current_label = label
    _current_session_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}-{label}"
    _started_ts = time.time()
    
    learning_stop_event.clear()
    learning_active = True
    set_mode("teach") 
    
    # Start actual learning thread
    thread = threading.Thread(
        target=start_learning_session, 
        kwargs={"session_name": _current_session_id, "stop_event": learning_stop_event}
    )
    thread.start()
    
    return _current_session_id

def stop_session() -> Optional[str]:
    """Stop learning session - enhanced stopping"""
    global _current_session_id, _current_label, _started_ts, learning_active
    
    print("[🛑] Stop session requested")
    
    # Force set the stop event
    learning_stop_event.set()
    learning_active = False
    set_mode("idle") 
    
    # Give threads time to stop gracefully
    import time
    time.sleep(1)
    
    # Get the session ID before clearing it
    sid = _current_session_id
    _current_session_id = None
    _current_label = None
    _started_ts = None
    
    print(f"[✅] Session {sid} stopped")
    return sid

def finalize_session(session_name: Optional[str] = None) -> Optional[str]:
    """Finalize current session with optional custom name"""
    global _current_session_id, _current_label, _started_ts, learning_active
    
    if not _current_session_id:
        raise ValueError("No active session to finalize")
    
    print(f"[💾] Finalizing session: {_current_session_id}")
    
    # Stop recording
    learning_stop_event.set()
    learning_active = False
    set_mode("idle")
    
    # If custom name provided, rename the session directory
    if session_name:
        old_path = LEARNING_LOGS_DIR / _current_session_id
        new_session_id = f"{session_name}_{int(time.time())}"
        new_path = LEARNING_LOGS_DIR / new_session_id
        
        if old_path.exists():
            old_path.rename(new_path)
            print(f"[📁] Renamed session: {_current_session_id} → {new_session_id}")
            finalized_id = new_session_id
        else:
            finalized_id = _current_session_id
    else:
        finalized_id = _current_session_id
    
    # Clear current session
    _current_session_id = None
    _current_label = None
    _started_ts = None
    
    print(f"[✅] Session finalized: {finalized_id}")
    return finalized_id

# ===== STATUS AND MONITORING =====
def learning_status():
    """Return current learning session status - FIXED VERSION"""
    
    # If we have an active session, use it directly
    if _current_session_id and learning_active:
        # Look for the current session directory (may have timestamp suffix)
        session_dirs = list(LEARNING_LOGS_DIR.glob(f"{_current_session_id}*"))
        
        if session_dirs:
            latest_session = session_dirs[0]  # Should only be one match
            session_id = latest_session.name
        else:
            print(f"[⚠️] Current session directory not found: {_current_session_id}")
            return {"recording": learning_active, "actions": [], "session_id": _current_session_id}
    else:
        # No active session - find most recent session directory
        if not LEARNING_LOGS_DIR.exists():
            return {"recording": False, "actions": [], "session_id": None}
        
        # Look for ANY session directory (not just "from_ui_*")
        session_dirs = [d for d in LEARNING_LOGS_DIR.iterdir() if d.is_dir()]
        
        if not session_dirs:
            return {"recording": False, "actions": [], "session_id": None}
        
        latest_session = max(session_dirs, key=lambda x: x.stat().st_ctime)
        session_id = latest_session.name
    
    # Read session log file
    log_file = latest_session / "learning_id.json"
    actions = []
    
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                file_content = f.read().strip()
                if file_content:
                    events_data = json.loads(file_content)
                    
                    for event in events_data:
                        event_type = event.get("event")
                        
                        if event_type == "click":
                            actions.append({
                                "id": len(actions) + 1,
                                "type": "click",
                                "element": f"{event.get('window', {}).get('title', 'Unknown')} in {event.get('app', 'Unknown')}",
                                "coordinates": event.get('raw_position', [0, 0]),
                                "timestamp": parse_event_timestamp(event),  
                                "description": clean_event_description("click", event)  
                            })
                        
                        elif event_type == "key":
                            key_value = event.get('key', '')
                            app_name = event.get('app', 'System')
                            
                            actions.append({
                                "id": len(actions) + 1,
                                "type": "key",
                                "element": f"Keyboard in {app_name}",
                                "coordinates": [0, 0],
                                "text": key_value,
                                "timestamp": parse_event_timestamp(event),  
                                "description": clean_event_description("key", event)  
                            })
                        
                        elif event_type == "type":
                            typed_text = event.get('text', '')
                            app_name = event.get('app', 'System')
                            
                            actions.append({
                                "id": len(actions) + 1,
                                "type": "type",
                                "element": f"Text Field in {app_name}",
                                "coordinates": [0, 0],
                                "text": typed_text,
                                "timestamp": parse_event_timestamp(event),
                                "description": clean_event_description("type", event)
                            })
        except Exception as e:
            print(f"[❌] Error reading session log: {e}")
    
    print(f"[📊] Returning {len(actions)} actions for session: {session_id}")
    
    return {
        "recording": learning_active,
        "mode": CURRENT_MODE,
        "actions": actions,
        "session_id": session_id,
        "action_count": len(actions)
    }

def list_learning_sessions():
    """List all available learning sessions - FIXED VERSION"""
    try:
        if not LEARNING_LOGS_DIR.exists():
            return {"sessions": []}
        
        sessions = []
        # FIXED: Look for ALL session directories, not just "from_ui_*"
        session_dirs = [d for d in LEARNING_LOGS_DIR.iterdir() if d.is_dir()]
        
        for session_dir in session_dirs:
            session_id = session_dir.name
            log_file = session_dir / "learning_id.json"
            
            if log_file.exists():
                action_count = 0
                try:
                    with open(log_file, 'r') as f:
                        content = f.read().strip()
                        if content:
                            events = json.loads(content)
                            action_count = len(events)
                except:
                    action_count = 0
                
                sessions.append({
                    "learning_id": session_id,
                    "file_path": str(log_file),
                    "created": session_dir.stat().st_ctime,
                    "action_count": action_count,
                    "status": "ready_for_export"
                })
        
        return {"sessions": sorted(sessions, key=lambda x: x["created"], reverse=True)}
        
    except Exception as e:
        return {"error": f"Failed to list sessions: {str(e)}", "sessions": []}
    
def debug_session_paths():
    """Debug function to show session discovery"""
    print(f"[DEBUG] Learning logs directory: {LEARNING_LOGS_DIR}")
    print(f"[DEBUG] Directory exists: {LEARNING_LOGS_DIR.exists()}")
    
    if LEARNING_LOGS_DIR.exists():
        all_items = list(LEARNING_LOGS_DIR.iterdir())
        print(f"[DEBUG] All items in learning_logs: {[item.name for item in all_items]}")
        
        session_dirs = [d for d in all_items if d.is_dir()]
        print(f"[DEBUG] Session directories: {[d.name for d in session_dirs]}")
        
        for session_dir in session_dirs:
            json_file = session_dir / "learning_id.json"
            print(f"[DEBUG] Session {session_dir.name} has JSON: {json_file.exists()}")
    
    return {"debug_complete": True}

# # ===== FASTAPI ROUTER ENDPOINTS =====
# # Only define these endpoints if FastAPI router is available
# try:
#     # Basic Session Control
#     @router.post("/start")
#     def api_start_learning():
#     """Start a new learning session via API"""
#     session_id = start_session("from_ui")
#     return {"status": "learning started", "active": True, "session_id": session_id}
# 
# @router.post("/stop")
# def api_stop_learning():
#     """Stop the current learning session via API"""
#     session_id = stop_session()
#     return {"status": "learning stopped", "active": False, "session_id": session_id}
# 
# @router.post("/clear")
# def close_learning_session():
#     """Close the current learning session"""
#     try:
#         session_id = stop_session()
#         return {
#             "status": "session closed", 
#             "success": True,
#             "message": "Learning session closed. Data preserved for export/loading.",
#             "active": False,
#             "session_id": session_id
#         }
#     except Exception as e:
#         print(f"[ERROR] Failed to close session: {e}")
#         return {
#             "status": "error",
#             "success": False, 
#             "error": str(e)
#         }
# 
# # Advanced Session Management
# @router.post("/finalize")
# def api_finalize_learning(session_name: str = None):
#     """Finalize current learning session with optional name"""
#     try:
#         finalized_id = finalize_session(session_name)
#         return {
#             "status": "session finalized", 
#             "success": True,
#             "session_id": finalized_id,
#             "message": f"Session finalized as: {finalized_id}"
#         }
#     except Exception as e:
#         return {
#             "status": "error",
#             "success": False, 
#             "error": str(e)
#         }
# 
# @router.post("/new")
# def api_new_learning_session(label: str = "new_session"):
#     """Start a completely new learning session (stops current if active)"""
#     try:
#         # Stop any current session first
#         if get_current_session_id():
#             stop_session()
#         
#         # Start fresh session
#         session_id = start_session(label)
#         return {
#             "status": "new session started", 
#             "active": True, 
#             "session_id": session_id,
#             "message": "Fresh learning session started"
#         }
#     except Exception as e:
#         return {
#             "status": "error",
#             "success": False,
#             "error": str(e)
#         }
# 
# # Session Pause/Resume
# @router.post("/pause")
# def teach_pause():
#     """Pause current learning session without ending it"""
#     learning_stop_event.set()  # Pause recording
#     learning_active = False
#     return {"status": "paused", "session_id": get_current_session_id()}
# 
# @router.post("/resume")
# def teach_resume():
#     """Resume current learning session"""
#     learning_stop_event.clear()  # Resume recording
#     learning_active = True
#     return {"status": "resumed", "session_id": get_current_session_id()}
# 
# 
# # Session Data Access
# @router.get("/status")
# def api_learning_status():
#     """Get current learning session status"""
#     return learning_status()
# 
# @router.get("/sessions")
# def api_list_learning_sessions():
#     """List all available learning sessions"""
#     return list_learning_sessions()
# 
# @router.post("/load/{session_id}")
# def load_learning_session(session_id: str):
#     """Load a specific learning session by ID"""
#     try:
#         # Stop any active learning first
#         stop_session()
#         
#         # Find the requested session
#         session_path = LEARNING_LOGS_DIR / session_id
#         
#         if not session_path.exists():
#             return {
#                 "status": "error",
#                 "success": False,
#                 "error": f"Session '{session_id}' not found"
#             }
#         
#         log_file = session_path / "learning_id.json"
#         
#         if not log_file.exists():
#             return {
#                 "status": "error", 
#                 "success": False,
#                 "error": f"Session data file not found for '{session_id}'"
#             }
#         
#         # Read session data
#         try:
#             with open(log_file, 'r') as f:
#                 content = f.read().strip()
#                 if content:
#                     events = json.loads(content)
#                     action_count = len(events)
#                 else:
#                     events = []
#                     action_count = 0
#         except Exception as e:
#             return {
#                 "status": "error",
#                 "success": False, 
#                 "error": f"Failed to read session data: {str(e)}"
#             }
#         
#         return {
#             "status": "session loaded",
#             "success": True,
#             "session_id": session_id,
#             "action_count": action_count,
#             "actions": events,
#             "message": f"Loaded session '{session_id}' with {action_count} actions"
#         }
#         
#     except Exception as e:
#         print(f"[ERROR] Failed to load session: {e}")
#         return {
#             "status": "error",
#             "success": False,
#             "error": str(e)
#         }
# 
# # Automation Integration
# @router.post("/auto/stop")
# def api_stop_auto():
#     """Hard-stops self-drive ('auto') mode and sets backend to idle"""
#     set_mode("idle")
#     learning_stop_event.set()  # in case self-drive re-uses same event
#     return {"status": "auto stopped", "active": False, "mode": "idle"}
# 
# # Health Check
# @router.get("/ping")
# def ping():
#     """Health check for learning API"""
#     return {
#         "status": "learning api live", 
#         "active_session": learning_active,
#         "current_session_id": _current_session_id,
#         "logs_directory": str(LEARNING_LOGS_DIR),
#         "logs_exist": LEARNING_LOGS_DIR.exists()
#     }
# 
# # Convert to Codex
# @router.get("/convert/{session_id}")
# def api_convert_session(session_id: str):
#     """Convert learning session to automation steps"""
#     try:
#         # Import the conversion logic
#         from learning_to_codex import AutomationConverter
#         
#         # Fix path inconsistency - use the actual logs directory
#         converter = AutomationConverter()
#         # Override the incorrect path in the converter
#         converter.learning_logs_path = LEARNING_LOGS_DIR
#         
#         # Convert session
#         automation = converter.convert_to_automation(session_id)
#         
#         return {
#             "success": True,
#             "automation": automation,
#             "steps": len(automation.get("steps", [])),
#             "message": f"Converted {len(automation.get('steps', []))} steps from session {session_id}"
#         }
#         
#     except FileNotFoundError as e:
#         return {
#             "success": False,
#             "error": f"Session not found: {session_id}",
#             "details": str(e)
#         }
#     except Exception as e:
#         print(f"[ERROR] Conversion failed for {session_id}: {e}")
#         return {
#             "success": False,
#             "error": f"Conversion failed: {str(e)}",
#             "session_id": session_id
#         }
