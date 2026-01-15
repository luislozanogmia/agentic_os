import os
from datetime import datetime
import time
from pynput import mouse
import pyautogui
from PIL import ImageGrab, ImageDraw
from AppKit import NSWorkspace
import threading
from system_info import get_last_active_app, enrich_mouse_event, get_timestamp
from log_writer import set_log_path, append_to_log
# from screenshot_taker import take_cropped_screenshot  # Optional: comment out if not available
from system_info import get_elements_near_point, is_accessibility_ready

# === Optional screen-normalized click ===
def normalize_position(x, y):
   screen_width, screen_height = pyautogui.size()
   return round(x / screen_width, 4), round(y / screen_height, 4)

# === Global state for window tracking ===
last_title = None
last_app = None

# === Click Event Handler (centralized) ===
def on_click(x, y, button, pressed, log_path, screen_dir=None):
    global last_title, last_app

    if not pressed:
       return  # Only log mouse down
   
    time.sleep(0.05)

    input_timestamp = get_timestamp()
    button_name = str(button).lower().replace("button.", "")
   
    # Create raw mouse event (pure event capture)
    raw_event = {
        "event": "click",
        "button": button_name,
        "coordinates": [x, y],
        "input_timestamp": input_timestamp
    }

    # Enrich with app/window context using clean API
    enriched_event = enrich_mouse_event(raw_event)
    if enriched_event is None:
        return  # Skip logging MIA Beta control events

   # ADD AX BUTTON DETECTION
    from system_info import get_elements_near_point, is_accessibility_ready, debug_ax_status

    debug_ax_status()
    
    print(f"[🔍 DEBUG] AX Ready Check: {is_accessibility_ready()}")

    if is_accessibility_ready():
        ax_candidates = get_elements_near_point(x, y)
        print(f"[🔍 DEBUG] AX Candidates found: {len(ax_candidates) if ax_candidates else 0}")

        if ax_candidates and len(ax_candidates) > 0:
            best = ax_candidates[0]
            print(f"[🔍 DEBUG] Best candidate: name='{best['name']}', role='{best['role']}', score={best['score']}")

            # ENHANCED: Capture full AX structure for conscious execution
            enriched_event["button_name"] = best["name"]
            enriched_event["ax_role"] = best["role"] 
            enriched_event["detection_method"] = "accessibility"
            enriched_event["ax_confidence"] = best["score"]
            enriched_event["ax_candidates_count"] = len(ax_candidates)
            
            # NEW: Full AX structure capture
            enriched_event["ax_data"] = {
                "identifier": None,  # Will be populated if available from element
                "role": best["role"],
                "title": best["name"], 
                "bounds": best["bounds"],  # for debugging only
                "enabled": best["enabled"],
                "actionable": best["actionable"],
                "confidence": best["score"],
                "detection_method": best.get("detection_method", "accessibility"),
                "distance": best["distance"]
            }
            
            # Extract AX identifier if element available
            if best.get("element"):
                try:
                    from system_info import _ax
                    if _ax.is_ready():
                        identifier_err, identifier_val = _ax.ax_get(
                            best["element"], 
                            _ax.constants.get("kAXIdentifierAttribute", "AXIdentifier")
                        )
                        if identifier_err == 0 and identifier_val:
                            enriched_event["ax_data"]["identifier"] = str(identifier_val)
                except Exception as e:
                    print(f"[🔍 DEBUG] Could not extract AX identifier: {e}")
            
            # Store top 3 candidates for fallback options
            enriched_event["ax_candidates"] = [
                {
                    "name": c["name"],
                    "role": c["role"], 
                    "bounds": c["bounds"],
                    "score": c["score"],
                    "enabled": c["enabled"],
                    "actionable": c["actionable"],
                    "detection_method": c.get("detection_method", "accessibility")
                } for c in ax_candidates[:3]  # Top 3 candidates
            ]
            
            print(f"[🔍 ENHANCED] Captured AX data: identifier={enriched_event['ax_data'].get('identifier')}, bounds={enriched_event['ax_data']['bounds']}")
            
        else:
            enriched_event["button_name"] = f"{enriched_event['app']} Button"
            enriched_event["detection_method"] = "position_heuristic"
            # Add heuristic data structure for consistency
            enriched_event["ax_data"] = {
                "identifier": None,
                "role": "Button",
                "title": f"{enriched_event['app']} Button",
                "bounds": [x - 25, y - 25, 50, 50],  # Estimated bounds
                "enabled": True,
                "actionable": True,
                "confidence": 75,  # Medium confidence for heuristics
                "detection_method": "position_heuristic",
                "distance": 0
            }
    else:
        enriched_event["button_name"] = f"{enriched_event['app']} Button"
        enriched_event["detection_method"] = "app_name_fallback"
        # Add fallback data structure for consistency
        enriched_event["ax_data"] = {
            "identifier": None,
            "role": "Button",
            "title": f"{enriched_event['app']} Button", 
            "bounds": [x - 25, y - 25, 50, 50],  # Estimated bounds
            "enabled": True,
            "actionable": True,
            "confidence": 50,  # Low confidence for fallback
            "detection_method": "app_name_fallback",
            "distance": 0
        }

    # Extract enriched data for tracking
    title = enriched_event.get("window_title", "Unknown")
    app = enriched_event.get("app", "Unknown")
    window = enriched_event.get("window", {})
    rel_x, rel_y = enriched_event.get("rel_position", [0.0, 0.0])
    norm_x, norm_y = enriched_event.get("position", [0.0, 0.0])

    if title != last_title or app != last_app:
        print(f"[🪟] Window changed to: {title} — App: {app}")
        last_title = title
        last_app = app

    # 📷 Screenshot with red dot  
    if screen_dir:
        try:
            from screenshot_taker import take_screenshot_with_red_dot, take_cropped_screenshot
           
            # Full screenshot with red dot
            screenshot_filename = f"{input_timestamp}.png"
            screenshot_path = take_screenshot_with_red_dot(
                x, y, screenshot_filename, folder=screen_dir, dot_radius=12
            )
           
            # Cropped screenshot for OCR
            crop_path = take_cropped_screenshot(x, y, crop_size=180, folder=screen_dir)
           
            # Add screenshot paths to enriched event
            enriched_event["screenshot"] = screenshot_path
            enriched_event["crop_screenshot"] = crop_path
           
        except Exception as e:
            print(f"[⚠️] Screenshot failed: {e}")

    # 💾 Save enriched event to log
    append_to_log(enriched_event)
    print(f"[🖱️] Click at ({x},{y}) → screen: ({norm_x:.2f},{norm_y:.2f}) | rel: ({rel_x:.2f},{rel_y:.2f}) in: '{title}' [App: {app}]")

# === Mouse Tracker Entrypoint ===
def run_mouse_tracker(log_path, screen_dir, stop_event=None):
   if log_path is None:
       # Get the absolute path of this script (should be in mia_desktop/learning/)
       script_dir = os.path.dirname(os.path.abspath(__file__))
       LOG_DIR = os.path.join(script_dir, "learning_logs")
       os.makedirs(LOG_DIR, exist_ok=True)
       log_path = os.path.join(LOG_DIR, "input_timestamp.json")

   set_log_path(log_path)
   print(f"[🧠] Mouse tracker started — logging to {log_path}")

   # Setup screen_dir for local screenshots
   session_dir = os.path.dirname(log_path)
   screen_dir = os.path.join(session_dir, "screens")

   # Wrapper to inject log_path + screen_dir
   def handler(x, y, button, pressed):
       on_click(x, y, button, pressed, log_path, screen_dir)

   # Start listener
   listener = mouse.Listener(on_click=handler)
   listener.start()
   
   # --- Start active app logging thread ---
   def log_active_app_loop():
       last_logged = None
       while True:
           if stop_event and stop_event.is_set():
               break
           active = get_last_active_app()
           if active and active != last_logged:
               print(f"[🧩] Detected active app: {active}")
               last_logged = active
           time.sleep(3)

   threading.Thread(target=log_active_app_loop, daemon=True).start()
   
   # Check for stop signal instead of listener.join()
   try:
       while True:
           if stop_event and stop_event.is_set():
               print("[🛑] Mouse tracker stopping...")
               break
           time.sleep(0.1)
   finally:
       listener.stop()

# === CLI Run ===
if __name__ == "__main__":
   run_mouse_tracker(None, None)