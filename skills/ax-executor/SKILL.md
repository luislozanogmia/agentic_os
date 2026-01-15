---
name: ax-executor
description: Find and click UI elements on any macOS application using the Accessibility framework. Works with system Python (/usr/bin/python3) or .claude/.venv with PyObjC installed.
allowed-tools: Bash(/usr/bin/python3:*), Bash(open:*), Bash(sleep:*), Read
---

# AX Executor Skill - Universal Clicking for ALL macOS Apps

## What This Is

This Skill teaches you to use **ax_search_and_click.py** - a **universal tool for finding and clicking UI elements on ANY macOS application** using the AX (Accessibility) framework.

**Why this matters**: Once you can see an element on your screen, you can click it - regardless of what app you're using. The AX framework searches by element labels (what users see), not coordinates or selectors. This works the same way on every application.

**Location**: `~/.claude/ax_search_and_click.py`

**Universal Pattern**: See element on screen → Search by its label → Click it. **Works everywhere.**

## Python Requirements

**Option 1: System Python (No setup needed)**
```bash
/usr/bin/python3 ax_executor_skill.py "element" --axfull
```

**Option 2: Virtual Environment (requires PyObjC)**
```bash
# Install PyObjC in your venv
pip install pyobjc pyobjc-framework-Cocoa

# Then run from venv
python3 ax_executor_skill.py "element" --axfull
```

Both work identically. The key requirement is **PyObjC** for Accessibility framework access.

## Core Pattern: Search → Find → Click

The pattern is simple:
1. **Know what to search for** (element label: "Login Button", "Home - Replit", etc)
2. **Search the AX tree** for that label
3. **Get coordinates** from the found element
4. **Click** using those coordinates

All in one command:
```bash
python3 ~/.claude/ax_search_and_click.py "element name" --click
```

## One-Command Usage

### Basic Search (Without Clicking)
```bash
python3 ~/.claude/ax_search_and_click.py "element name"
```

Returns: element found, role, label, coordinates, frame

### Search and Click
```bash
python3 ~/.claude/ax_search_and_click.py "element name" --click
```

Returns: success confirmation + element details

## Real Examples - Works on ANY App

### Example 1: Click Contact in WhatsApp
```bash
python3 ~/.claude/ax_search_and_click.py "John Doe" --click
```

Finds and clicks "John Doe" contact. **Works because you see it on screen.**

Output:
```
✅ FOUND!
  Role:   AXMenuBarItem
  Label:  John Doe
  Score:  0.950
  Frame:  (234, 120) 48×32
  Center: (258, 136)
✅ Clicked!
```

### Example 2: Click Button in VS Code
```bash
python3 ~/.claude/ax_search_and_click.py "Run Code" --click
```

Finds "Run Code" button in VS Code editor and clicks it. **Same tool, different app.**

### Example 3: Search Chrome Without Clicking
```bash
python3 ~/.claude/ax_search_and_click.py "mia labs"
```

Finds all matching elements on screen, shows details, doesn't click. Works in Chrome, Safari, Firefox, anywhere.

### Example 4: Click Browser Tab
```bash
python3 ~/.claude/ax_search_and_click.py "Home - Replit" --click
```

Finds browser tab or window titled "Home - Replit" and clicks it. Works in any browser.

### Example 5: Click Mail App Button
```bash
python3 ~/.claude/ax_search_and_click.py "New Message" --click
```

Finds "New Message" button in Mail app and clicks it. **Universal.**

### Example 6: Click Finder Window
```bash
python3 ~/.claude/ax_search_and_click.py "Documents" --click
```

Finds folder in Finder and clicks it. Works the same as every other app.

## How It Works Internally

1. **Get frontmost app**
   - Uses NSWorkspace to find active application
   - Gets app PID and name

2. **Create AX root element**
   - Creates accessibility element from app PID
   - Root gives access to entire app hierarchy

3. **Search AX tree**
   - Uses `ax_full_window_strict_search()`
   - Searches by label (what users see)
   - Supports fuzzy matching for partial labels
   - Max 5000 nodes searched, max depth 25

4. **Extract element frame**
   - Gets x, y, width, height from element
   - Calculates center point
   - Frame determines click location

5. **Click if requested**
   - Uses `click(center_x, center_y)`
   - Sends mouse event to system
   - Reports success/failure

## Key Advantages

✅ **Label-based searching** (not coordinates)
- Survives UI layout changes
- Human-readable element names
- Robust across app updates

✅ **Fuzzy matching**
- "John" finds "John Doe"
- "home" finds "Home - Replit"
- Partial names work

✅ **Scoring/ranking**
- Multiple matches ranked by relevance
- Best match returned first
- See match score (0.0-1.0)

✅ **Frame visibility**
- Know exact coordinates before clicking
- Can verify element location
- Debug mode shows all found elements

## When to Use This Skill

✅ **Use ax_search_and_click for ANY situation where**:
- You can SEE an element on your screen (regardless of app)
- You need to click a button, link, or UI element
- You need to interact with Chrome, Safari, Firefox, VS Code, Mail, Slack, Finder, or ANY macOS application
- You need to navigate tabs, windows, or UI controls
- You need to find an element by its visible label
- You're doing **universal UI automation** across all apps

**Key insight:** If the element is visible on screen, this tool can click it - works the same everywhere.

❌ **Don't use when**:
- Element is not visible/not clickable on screen
- You need scrolling first (use keyboard scrolling instead)
- Element label is dynamic/changes frequently
- You need complex keyboard input (use keyboard tools instead)

## Troubleshooting

### Element Not Found

If search returns "NOT FOUND":

1. **Check the label**
   ```bash
   # Try with just "John" instead of full name
   python3 ~/.claude/ax_search_and_click.py "John" --click
   ```

2. **Check the app is frontmost**
   ```bash
   # Make sure the app window is in focus
   # Use open -a "AppName" first if needed
   ```

3. **Check element is visible**
   - Element must be on screen and not hidden
   - Hidden/greyed-out elements might not match

4. **Use partial names**
   - "Alex" instead of "John Doe"
   - "home" instead of "Home - Replit"

### Low Match Score

If found but score < 0.8:

- Element label might be partially visible
- Similar elements nearby
- Try more specific label substring
- Use full visible label for better match

## Advanced: Direct Python Usage

For programmatic use in scripts:

```python
import sys
sys.path.insert(0, '{{HOME}}/.claude')

from ax_executor import (
    AXUIElementCreateApplication,
    ax_full_window_strict_search,
    click
)

# Get app and search
pid = 1234  # app PID
root_el = AXUIElementCreateApplication(pid)

search_target = {"best_label": "Button Name", "role": None}
best_el, best_info, best_score, nodes = ax_full_window_strict_search(
    search_target, root_el, max_depth=25, max_nodes=5000
)

# Click if found
if best_el and best_score > 0.8:
    frame = best_info.get('frame')
    click((frame['x'] + frame['w']/2, frame['y'] + frame['h']/2))
```

## Pattern in Practice

**Master Pattern**: Screenshot → Look → Identify → Search → Click

```
1. Take screenshot (see current state)
2. Visually identify what you need
3. Find element by visible label
4. Use ax_search_and_click.py
5. Verify result with next screenshot
```

## Workflow Recording - Teach-by-Demonstration

Record manual workflows and replay them deterministically. Perfect for building reusable automation.

### What Gets Recorded

- ✅ Search labels (what you searched for)
- ✅ Complete AX element metadata (role, description, attributes)
- ✅ App context (app name, PID, window bounds)
- ✅ Execution coordinates (where you clicked)
- ✅ Confidence scores (how confident the match was)
- ✅ Timing and sequencing (when each step happened)

### Quick Start: Record a Workflow

**Option A: Terminal Commands**

**Step 1: Start Recording**
```bash
python3 ~/.claude/skills/ax-executor/ax_executor_skill.py --record "post_on_linkedin"
```

Output:
```
[🎬] Recording session started: 1704334923-a1b2c3d4-post_on_linkedin
[📝] Recording session started. Execute searches with --axfull to record steps.
```

**Step 2: Execute Steps (Use `--axfull` to auto-record)**
```bash
# Each step is automatically recorded
python3 ~/.claude/skills/ax-executor/ax_executor_skill.py "john" --axfull
# Output: ✅ FOUND! [📝] Step recorded: search 'john'

python3 ~/.claude/skills/ax-executor/ax_executor_skill.py "message" --axfull
# Output: ✅ FOUND! [📝] Step recorded: search 'message'

python3 ~/.claude/skills/ax-executor/ax_executor_skill.py "send" --axfull
# Output: ✅ FOUND! [📝] Step recorded: search 'send'
```

**Step 3: Stop Recording**
```bash
python3 ~/.claude/skills/ax-executor/ax_executor_skill.py --stop-record
```

Output:
```
[🛑] Stop session requested
[✅] Learning session completely stopped
[🎬] Recording session finalized: 1704334923-a1b2c3d4-post_on_linkedin
```

**Option B: Floating UI Control Panel (For User Interaction Only)**

⚠️ **THIS IS A USER-FACING TOOL** - You use it by clicking, not Claude.

Start the floating recording control panel (requires PyObjC):

**From ~/.claude directory (easiest):**
```bash
cd ~/.claude && python3 skills/ax-executor/recording_ui.py
```

**Or from ax-executor directory:**
```bash
cd ~/.claude/skills/ax-executor && python3 recording_ui.py
```

**Or with full path + venv:**
```bash
~/.claude/.venv/bin/python3 ~/.claude/skills/ax-executor/recording_ui.py
```

**Or with system Python:**
```bash
/usr/bin/python3 ~/.claude/skills/ax-executor/recording_ui.py
```

A small floating macOS window appears with:
- **Record** button - Click to start recording (auto-generates workflow name)
- **Stop** button - Click to finalize recording
- Status display showing recording state
- Instructions for executing searches

**Advantages:**
- ✅ Click anywhere on your screen (window stays floating)
- ✅ No terminal switching needed
- ✅ Visual feedback of recording state
- ✅ Perfect for interactive workflows
- ✅ Doesn't interrupt your automation work

**Workflow with Floating UI (User-Driven):**
1. Run `python3 recording_ui.py` in one terminal
2. **You click Record** button to start session
3. **You execute your workflow** in other apps:
   - Mouse and keyboard events are captured automatically
   - Can use `ax_executor_skill.py "element"` for plain search
   - Can use `ax_executor_skill.py "element" --axfull` for additional L0-L7 validation data
4. **You click Stop** button when done
5. Workflow is saved to `learning_logs/` with complete event sequence

### Record and Execute in One Command

```bash
python3 ~/.claude/skills/ax-executor/ax_executor_skill.py "john" --axfull --record "post_on_linkedin"
```

This starts recording AND executes the step, leaving session running for more steps.

### Recording Flags

```bash
--record [name]           # Start recording session (optional workflow name)
--stop-record             # Stop and finalize recording session
```

### Where Recordings Are Stored

```
~/.claude/skills/ax-executor/learning_logs/
└── post_on_linkedin_2026-01-02_23-41-30/
    ├── learning_id.json   # All recorded steps (JSON)
    └── screens/           # Optional screenshots
```

Each recorded workflow is a JSON file containing:
```json
[
  {
    "type": "workflow_step",
    "step_type": "search",
    "search_label": "john",
    "app_context": {"name": "WhatsApp", "pid": 682},
    "element_info": {"AXRole": "AXButton", "AXDescription": "John Doe"},
    "confidence_score": 0.95,
    "execution_coords": [494.5, 402.5],
    "frame": {"x": 470, "y": 390, "w": 50, "h": 25},
    "timestamp": "2026-01-02 23:41:30"
  }
  // ... more steps
]
```

### Recording Best Practices

✅ **Do**:
- Use `--axfull` for maximum data and L0-L7 validation
- Give workflows meaningful names (`post_on_linkedin`, not `workflow`)
- Record in consistent app state (one app at a time)
- Keep workflows focused (5-20 steps ideal)
- Verify each step as you go (check FOUND! message)

❌ **Avoid**:
- Switching apps mid-recording
- Using dynamic element labels
- Time-dependent logic
- Mixing recording and replay in same session

### Integration with AM_Beta

Recording uses AM_Beta's proven learning infrastructure:
- **learning_api.py** - Session management
- **log_writer.py** - Thread-safe JSON logging
- **mouse_tracker.py** - Optional UI event capture
- **keyboard_tracker.py** - Optional text input capture

Session data is timestamped and organized for reproducible automation.

## Rules

✅ **Always**:
- Know what element you're searching for before calling
- Use visible labels (what users see)
- Verify with screenshots before and after
- Use `--axfull` when recording for maximum data

❌ **Never**:
- Try to click hidden elements
- Use selectors/CSS (use labels instead)
- Assume coordinates (let AX find them)
- Click without verifying element is found

## Hardcoded Automation Pattern - wake_claude.py Example

**Problem:** Recording interactions with test_ax_execute.py is useful for development, but using them repeatedly requires modifying inspector.json references each time.

**Solution:** Create hardcoded automation scripts that:
1. Use frozen JSON files (`wake_claude.json` copied from `inspector.json`)
2. Are self-contained and reusable via task queue
3. Can be scheduled or triggered programmatically
4. Support dynamic input via CLI flags (e.g., `--type "message"`)

### The Pattern

**File Structure:**
```
~/.claude/skills/ax-executor/
├── wake_claude.json          # Frozen element data (copy of inspector.json)
├── wake_claude.py            # Hardcoded automation script
└── [repeat pattern for other automations]
```

**wake_claude.py Structure:**
```python
class WakeClaudeCLI:
    def __init__(self):
        self.engine = AXEngine()
        # Hardcoded filename - no argument parsing complexity
        self.inspector_path = "wake_claude.json"

    def run(self, argv):
        # Load element from wake_claude.json (always index 0)
        rec, total, sel = self.engine.load_recorded_step(self.inspector_path, 0)
        # Execute click with L0-L7 validation pipeline
        success = self.engine.execute_step(rec, do_click=True)
        # Optional: type message via --type flag
        if to_type:
            paste_and_send(to_type)
        return success
```

### Usage in Task Queue

Single command that:
1. Focuses VS Code
2. Waits for window to come to focus
3. Clicks message input field
4. Types and sends a message
5. Presses Enter

```bash
open -a "Visual Studio Code" && sleep 2 && \
cd ~/.claude/skills/ax-executor && \
python3 wake_claude.py --type "wake up claude check your results"
```

### Why This Pattern Works

✅ **Frozen element data survives UI changes** - Element position in file structure matters, not pixel coordinates
✅ **Task queue flexibility** - Trigger anytime with different messages via `--type`
✅ **No CLI complexity** - Index 0 is always the target, no argument parsing needed
✅ **Replicable** - Copy wake_claude.json → new_action.json, copy wake_claude.py → new_action.py, update filename
✅ **Debuggable** - Full L0-L7 pipeline output shows exactly where/why clicks fail
✅ **Safe** - Uses same AX Executor validation engine, cannot cause destruction

### Creating New Automations

**Step-by-step template:**

```bash
# 1. Record element interaction (generates inspector.json)
python3 test_ax_inspector.py

# 2. Freeze the element data
cp inspector.json send_email.json

# 3. Create automation script
cp wake_claude.py send_email.py

# 4. Edit send_email.py - change one line:
#    self.inspector_path = "send_email.json"

# 5. Add to task queue
curl -X POST http://localhost:5050/tasks \
  -H "Content-Type: application/json" \
  -d '{"description": "Send email",
       "command": "cd ~/.claude/skills/ax-executor && python3 send_email.py --type \"subject: test\""}'
```

### Real Example - Wake Claude Chat

**Files created:**
- `wake_claude.json` - Frozen element data for message input (AXTextArea)
- `wake_claude.py` - Hardcoded script that always clicks index 0, types message, sends

**Usage:**

Direct execution:
```bash
cd ~/.claude/skills/ax-executor && python3 wake_claude.py --type "hello"
```

Add to task queue anytime:
```bash
curl -s -X POST http://localhost:5050/tasks -H "Content-Type: application/json" -d '{"description": "Wake Claude and send message", "command": "open -a \"Visual Studio Code\" && sleep 2 && cd ~/.claude/skills/ax-executor && python3 wake_claude.py --type \"wake up claude check your results\""}' | python3 -m json.tool
```

Run pending tasks immediately:
```bash
curl -s -X POST http://localhost:5050/tasks/batch | python3 -m json.tool
```

This pattern enables building a library of reusable, scheduled automations without maintaining complex CLI tools.

## Related

**See also**:
- Screenshot tool for UI state verification before/after clicking
- Workflow replay system (coming next: load and replay recorded workflows)
- Task manager at localhost:5050 for scheduling hardcoded automations
