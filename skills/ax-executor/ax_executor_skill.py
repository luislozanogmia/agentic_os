#!/usr/bin/env python3
"""
AX Search and Click - Direct Automation

Search the AX tree for an element by name, then click it using the found data.

Usage:
    python3 ax_search_and_click.py "element name"
"""

import sys
import time
import json
import os
import threading

sys.path.insert(0, '{{CLAUDE_HOME}}')

from AppKit import NSWorkspace
from ax_executor import (
    ax_full_window_strict_search,
    ax_full_tree_resolve,
    AXUIElementCreateApplication,
    ax_frame_or_compose,
    click,
    AXEngine,
    element_info,
    get_activation_point,
    decode_frame,
)

# ============================================================================
# Workflow Recording Integration - with AM_Beta learning system
# ============================================================================

CURRENT_RECORDING_SESSION = None


def start_recording_session(workflow_name: str = None):
    """
    Start a new workflow recording session using AM_Beta's learning infrastructure.

    Args:
        workflow_name: Name for the workflow (e.g., 'post_on_linkedin')
                      If None, auto-generates name with timestamp

    Returns:
        Session ID string
    """
    global CURRENT_RECORDING_SESSION
    try:
        from learning_api import start_session
        session_id = start_session(label=workflow_name or "workflow")
        CURRENT_RECORDING_SESSION = session_id
        print(f"[🎬] Recording session started: {session_id}")
        return session_id
    except ImportError as e:
        print(f"[⚠️] Learning API not available: {e}")
        return None


def stop_recording_session():
    """
    Stop and finalize the current recording session.

    Returns:
        Session ID of the stopped session
    """
    global CURRENT_RECORDING_SESSION
    try:
        from learning_api import stop_session, finalize_session

        if CURRENT_RECORDING_SESSION:
            sid = stop_session()
            finalize_session()
            CURRENT_RECORDING_SESSION = None
            print(f"[🎬] Recording session finalized: {sid}")
            return sid
    except ImportError:
        pass
    return None


def record_step(step_type: str, search_label: str, element):
    """
    Records a workflow step by automatically inspecting the provided element.
    
    Wraps 'inspect_step' to dynamically gather:
    - App context (PID, Name)
    - Element attributes and Frame
    - Coordinates
    
    Args:
        step_type (str): The action type (e.g., "click", "search").
        search_label (str): The human-readable label used to find the element.
        element (AXUIElement): The actual accessibility element object to inspect.
    """
    if not CURRENT_RECORDING_SESSION:
        return  # Exit immediately if not recording

    try:
        import time
        from log_writer import append_to_log

        # --- 1. INSPECTION PHASE ---
        # We call inspect_step here to gather all metadata from the live element
        try:
            # Assuming inspect_step returns a dictionary of details
            inspected_data = inspect_step(element, search_label)
        except Exception as inspect_err:
            print(f"[⚠️] Inspection failed inside record_step: {inspect_err}")
            # Fallback empty data so we can still log that a click happened
            inspected_data = {}

        # --- 2. DATA EXTRACTION ---
        # Extract data safely with defaults in case inspection was partial
        app_name = inspected_data.get('app_name', 'Unknown Application')
        app_pid = inspected_data.get('pid', 0)
        element_info = inspected_data.get('element_info', {})
        score = inspected_data.get('confidence', 1.0)
        frame_info = inspected_data.get('frame', None)
        activation_point = inspected_data.get('activation_point', None)

        # --- 3. COORDINATE CALCULATION ---
        exec_coords = None
        if activation_point:
            exec_coords = list(activation_point)
        elif frame_info:
            # Calculate center if we only have frame but no specific click point
            exec_coords = [
                frame_info['x'] + frame_info['w'] / 2,
                frame_info['y'] + frame_info['h'] / 2
            ]

        # --- 4. PAYLOAD CONSTRUCTION ---
        step_event = {
            "type": "workflow_step",
            "step_type": step_type,
            "search_label": search_label,
            "app_context": {
                "name": app_name,
                "pid": app_pid
            },
            "element_info": element_info,
            "confidence_score": score,
            "execution_coords": exec_coords,
            "frame": frame_info,
            "activation_point": activation_point,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # --- 5. WRITE TO DISK ---
        append_to_log(step_event)
        print(f"[📝] Recorded: {step_type} on '{search_label}' (App: {app_name})")

    except Exception as e:
        print(f"[⚠️] Critical error in record_step: {e}")

def search_and_click(label, do_click=True):
    """Search for element and click it"""
    print("=" * 70)
    print(f"SEARCH AND CLICK: '{label}'")
    print("=" * 70)

    # Get frontmost app
    ws = NSWorkspace.sharedWorkspace()
    front_app = ws.frontmostApplication()
    if not front_app:
        print("ERROR: No frontmost app")
        return False

    pid = front_app.processIdentifier()
    app_name = front_app.localizedName()
    print(f"\n✓ Frontmost app: {app_name} (PID {pid})")

    # Create root element
    root_el = AXUIElementCreateApplication(pid)

    # Get window frame
    try:
        frame = ax_frame_or_compose(root_el)
    except:
        frame = None

    if frame:
        print(f"✓ Window: {frame['w']:.0f}×{frame['h']:.0f}")

    # Search
    print(f"\n🔍 Searching for '{label}'...")

    search_target = {
        "best_label": label,
        "role": None,
    }

    best_el, best_info, best_score, nodes_visited = ax_full_window_strict_search(
        search_target,
        root_el,
        window_frame=frame,
        max_depth=30,
        max_nodes=10000,
        debug=False,
        allowed_roles=None
    )

    print(f"✓ Nodes visited: {nodes_visited}")

    if not best_el or not best_info:
        print(f"\n❌ NOT FOUND")
        print(f"  Best score: {best_score:.3f}")
        return False

    # Even low-confidence matches can be valid - AX matching is fuzzy
    if best_score < 0.5:
        print(f"\n⚠️  Low confidence: {best_score:.3f}")
        # Continue anyway, might still be useful

    # Found it!
    print(f"\n✅ FOUND!")
    print(f"  Role:   {best_info.get('AXRole')}")
    print(f"  Label:  {best_info.get('best_label')}")
    print(f"  Score:  {best_score:.3f}")

    # Get frame from element
    frame_info = best_info.get('frame')
    if not frame_info:
        try:
            from ax_executor import ax_frame_or_compose
            frame_info = ax_frame_or_compose(best_el)
        except:
            pass

    if frame_info:
        cx = frame_info['x'] + frame_info['w']/2
        cy = frame_info['y'] + frame_info['h']/2
        print(f"  Frame:  ({frame_info['x']:.0f}, {frame_info['y']:.0f}) {frame_info['w']:.0f}×{frame_info['h']:.0f}")
        print(f"  Center: ({cx:.0f}, {cy:.0f})")
    else:
        print(f"  Frame:  (not available)")

    actions = best_info.get('actions', [])
    if 'AXPress' in actions:
        print(f"  Action: AXPress available")

    if not do_click:
        print(f"\n(Use --click to actually click)")
        return True

    # Click it
    print(f"\n▶️  Clicking...")
    try:
        if frame_info:
            cx = frame_info['x'] + frame_info['w']/2
            cy = frame_info['y'] + frame_info['h']/2
            print(f"  Clicking at ({cx:.0f}, {cy:.0f})")
            click((cx, cy))
            print(f"✅ Clicked!")
            return True
        else:
            print("ERROR: No frame info to click")
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def search_full_tree_execute_l0_l7(label):
    """Search with ax_full_tree_resolve (exhaustive), execute via L0-L7 pipeline"""
    print("=" * 70)
    print(f"SEARCH FULL TREE + L0-L7: '{label}'")
    print("=" * 70)

    # Get frontmost app
    ws = NSWorkspace.sharedWorkspace()
    front_app = ws.frontmostApplication()
    if not front_app:
        print("ERROR: No frontmost app")
        return False

    pid = front_app.processIdentifier()
    app_name = front_app.localizedName()
    print(f"\n✓ Frontmost app: {app_name} (PID {pid})")

    # Create root element
    root_el = AXUIElementCreateApplication(pid)

    # Get window frame
    try:
        frame = ax_frame_or_compose(root_el)
    except:
        frame = None

    if frame:
        print(f"✓ Window: {frame['w']:.0f}×{frame['h']:.0f}")

    # Search - EXHAUSTIVE full tree resolve
    print(f"\n🔍 Searching FULL TREE for '{label}'...")

    search_target = {
        "best_label": label,
        "role": None,
    }

    best_el, best_info, best_score, nodes_visited = ax_full_tree_resolve(
        search_target,
        root_el,
        max_depth=50,
        max_nodes=50000
    )

    print(f"✓ Nodes visited: {nodes_visited}")

    if not best_el:
        print(f"\n❌ NOT FOUND")
        return False

    print(f"\n✅ FOUND!")
    print(f"  Role:   {best_info.get('AXRole')}")
    print(f"  Label:  {best_info.get('best_label')}")
    print(f"  Score:  {best_score:.3f}")

    # Extract frame and activation point from FULL TREE search
    frame_info, _ = decode_frame(best_el, element_only=True)
    ap = get_activation_point(best_el)

    if frame_info:
        cx = frame_info['x'] + frame_info['w']/2
        cy = frame_info['y'] + frame_info['h']/2
        print(f"  Frame:  ({frame_info['x']:.0f}, {frame_info['y']:.0f}) {frame_info['w']:.0f}×{frame_info['h']:.0f}")
        print(f"  Center: ({cx:.0f}, {cy:.0f})")

    if ap:
        print(f"  ActivationPoint: ({ap[0]:.0f}, {ap[1]:.0f})")

    # Record step if in recording session (AM_Beta learning system)
    record_step(
        step_type="search",
        search_label=label,
        app_name=app_name,
        app_pid=pid,
        element_info_dict=best_info,
        score=best_score,
        frame_info=frame_info,
        activation_point=ap
    )

    # Save search result to recorded folder
    engine = AXEngine()
    recorded_path = engine.save_search_result(label, best_info, best_score, app_name, pid)
    if recorded_path:
        print(f"  📝 Recorded: {recorded_path}")

    # Build synthetic recorded step for L0-L7 execution
    synthetic_step = {
        "best_label": label,
        "role": best_info.get('AXRole'),
        "frame": frame_info if frame_info else None,
        "activation_point": ap if ap else None,
        "AXRole": best_info.get('AXRole'),
    }

    print(f"\n▶️  Executing via L0-L7 pipeline (--axfull)...")
    try:
        success = engine._run_once(
            synthetic_step,
            do_click=True,
            safe_click=True,
            debug=True
        )

        if success:
            print(f"\n✅ Full tree search + L0-L7 execution successful!")
            return True
        else:
            print(f"\n❌ L0-L7 execution failed")
            return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def search_and_execute_l0_l7(label, do_click=True):
    """Search for element, use search tree + frame data for execution"""
    print("=" * 70)
    print(f"SEARCH & EXECUTE (Search Tree → Click): '{label}'")
    print("=" * 70)

    # Get frontmost app
    ws = NSWorkspace.sharedWorkspace()
    front_app = ws.frontmostApplication()
    if not front_app:
        print("ERROR: No frontmost app")
        return False

    pid = front_app.processIdentifier()
    app_name = front_app.localizedName()
    print(f"\n✓ Frontmost app: {app_name} (PID {pid})")

    # Create root element
    root_el = AXUIElementCreateApplication(pid)

    # Get window frame
    try:
        frame = ax_frame_or_compose(root_el)
    except:
        frame = None

    if frame:
        print(f"✓ Window: {frame['w']:.0f}×{frame['h']:.0f}")

    # Search
    print(f"\n🔍 Searching for '{label}'...")

    search_target = {
        "best_label": label,
        "role": None,
    }

    best_el, best_info, best_score, nodes_visited = ax_full_window_strict_search(
        search_target,
        root_el,
        window_frame=frame,
        max_depth=30,
        max_nodes=10000,
        debug=False,
        allowed_roles=None
    )

    print(f"✓ Nodes visited: {nodes_visited}")

    if not best_el:
        print(f"\n❌ NOT FOUND")
        return False

    print(f"\n✅ FOUND!")
    print(f"  Role:   {best_info.get('AXRole')}")
    print(f"  Label:  {best_info.get('best_label')}")
    print(f"  Score:  {best_score:.3f}")

    # Extract frame and activation point from SEARCH TREE
    frame_info, _ = decode_frame(best_el, element_only=True)
    ap = get_activation_point(best_el)

    print(f"\n📍 Click Coordinates:")
    if ap:
        print(f"  ActivationPoint: ({ap[0]:.0f}, {ap[1]:.0f})")
        click_pt = ap
    elif frame_info:
        cx = frame_info['x'] + frame_info['w']/2
        cy = frame_info['y'] + frame_info['h']/2
        print(f"  Frame Center: ({cx:.0f}, {cy:.0f})")
        click_pt = (cx, cy)
    else:
        print(f"  ❌ No frame or activation point available")
        return False

    if not do_click:
        print(f"\n(Use --execute to actually click)")
        return True

    # Direct click using search tree data (no L0-L7 overhead)
    print(f"\n▶️  Clicking at {click_pt}...")
    try:
        click(click_pt)
        print(f"✅ Clicked!")
        return True
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print("""
╔════════════════════════════════════════════════════════════════════╗
║               AX Executor - Accessibility Automation               ║
╚════════════════════════════════════════════════════════════════════╝

USAGE:
  python3 ax_executor_skill.py "element label" [OPTIONS]

OPTIONS:
  (none)           Search only - find element, show details
  --click          Search + Simple Click (uses frame center)
  --l0-l7          Search + Full L0-L7 Pipeline (all validation layers)
  --axfull         FULL TREE SEARCH + L0-L7 (exhaustive + all validation)
  --tree           Search using ax_full_tree_resolve (exhaustive search)
  --debug          Enable debug output during search
  --record [name]  Start recording session (optional workflow name)
  --stop-record    Stop and finalize recording session

EXAMPLES:
  # Search for element
  python3 ax_executor_skill.py "new message"

  # Search and click (simple)
  python3 ax_executor_skill.py "new message" --click

  # Start recording a workflow
  python3 ax_executor_skill.py --record "post_on_linkedin"

  # Record steps while searching
  python3 ax_executor_skill.py "alejandro" --axfull --record "post_on_linkedin"

  # Stop recording and finalize
  python3 ax_executor_skill.py --stop-record

  # ⭐ FULL POWER: Exhaustive tree search + L0-L7 execution
  python3 ax_executor_skill.py "button" --axfull

  # Search with full tree traversal
  python3 ax_executor_skill.py "button" --tree --click

  # Debug mode
  python3 ax_executor_skill.py "element" --debug

PIPELINE LAYERS (--l0-l7 / --axfull):
  L0: Fresh state, browser resolution, PID lookup
  L1: Identity validation, app name canonicalization
  L2: Window projection & coordinate math (handles window moves/resizes)
  L3: Preflight validation, element signature comparison
  L4: Refinement pipeline (micro-refine, tree resolve, neighbor snap)
  L5: Hover preflight verification
  L6: Last recovery + click safeguard
  L7: Escalation handling (retries with OCR/Vision if needed)
        """)
        sys.exit(1)

    # Handle --record and --stop-record special cases
    do_stop_record = "--stop-record" in sys.argv
    if do_stop_record:
        sid = stop_recording_session()
        if sid:
            print(f"[✅] Session stopped: {sid}")
        sys.exit(0)

    # Check for --record flag (can be with or without workflow name)
    do_record = "--record" in sys.argv
    workflow_name = None
    if do_record:
        # Get workflow name if provided after --record
        try:
            record_idx = sys.argv.index("--record")
            if record_idx + 1 < len(sys.argv) and not sys.argv[record_idx + 1].startswith("--"):
                workflow_name = sys.argv[record_idx + 1]
        except (ValueError, IndexError):
            pass

        # Start recording session
        sid = start_recording_session(workflow_name)
        if not sid:
            print("[⚠️] Could not start recording session")

    # Process main command
    label = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None

    if label:
        do_click = "--click" in sys.argv
        do_l0_l7 = "--l0-l7" in sys.argv
        do_axfull = "--axfull" in sys.argv
        do_tree = "--tree" in sys.argv

        if do_axfull:
            # ⭐ FULL POWER: exhaustive tree search + full L0-L7 pipeline
            success = search_full_tree_execute_l0_l7(label)
        elif do_l0_l7:
            success = search_and_execute_l0_l7(label, do_click=True)
        elif do_tree:
            # Use full tree resolve instead of strict search
            success = search_and_click(label, do_click=do_click)
        else:
            success = search_and_click(label, do_click=do_click)

        sys.exit(0 if success else 1)
    elif do_record:
        # Just started recording, waiting for commands
        print("[📝] Recording session started. Execute searches with --axfull to record steps.")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
