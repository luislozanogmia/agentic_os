---
name: chrome-control
description: Control Chrome by impersonating you using ax_executor + osascript. Works across all macOS apps. Searches by visible element labels, clicks to navigate. This is how to automate as a real user - not as a headless bot.
allowed-tools: Bash(osascript:*), Bash(open:*), Bash(sleep:*), Bash(screencapture:*), Read, Skill(ax-executor)
---

# Chrome Control Skill - User Impersonation via AX Framework + osascript

## What This Is

**One proven way to automate Chrome while impersonating you:**
- **AX_EXECUTOR + OSASCRIPT** - I search for elements by their visible labels (what you see) and interact with them the way you would
- No bot detection, no headless flags needed
- Works because it's indistinguishable from a real user clicking and typing

**Why CDP doesn't work on macOS:**
- `--remote-debugging-port` is deliberately designed to fail for security
- Port isn't actually exposed on macOS (unlike Linux/Windows)
- This is intentional - Apple doesn't want automation of browser automation

**The solution:**
- Use accessibility framework (AX) to find elements by their visible labels
- Use osascript to control the keyboard and mouse
- This impersonates you perfectly - you control Chrome the same way

## MANDATORY WORKFLOW: Command → Screenshot → Command → Screenshot

**CRITICAL**: Always alternate between single bash commands and screenshots. This prevents mistakes and permission issues.

```
Step 1: Execute ONE bash command (osascript or sleep)
Step 2: Take screenshot to verify state
Step 3: Execute ONE bash command (osascript or sleep)
Step 4: Take screenshot to verify state
... repeat until done
```

### Good (Always Do This)
```bash
# Step 1: Activate Chrome
osascript -e 'tell application "Google Chrome" to activate'

# Step 2: Screenshot to verify Chrome is focused
screencapture -x /tmp/screenshot.png

# Step 3: Focus address bar
osascript -e 'tell application "System Events" to keystroke "l" using command down'

# Step 4: Screenshot to verify address bar is focused
screencapture -x /tmp/screenshot.png

# Step 5: Type URL
osascript -e 'tell application "System Events" to keystroke "example.com"'

# Step 6: Screenshot to verify URL is typed
screencapture -x /tmp/screenshot.png

# Step 7: Press Enter
osascript -e 'tell application "System Events" to key code 36'

# Step 8: Wait for page to load
sleep 3

# Step 9: Screenshot to verify page loaded
screencapture -x /tmp/screenshot.png
```
✅ Each command separate = no permission issues, each step verifiable

## Keyboard Commands Reference

### Navigation
- **Cmd+L**: Focus address bar → `keystroke "l" using command down`
- **Enter**: Navigate → `key code 36`
- **Page Down**: Scroll one full page → `key code 121` (PREFERRED for browsing)
- **Page Up**: Scroll up one full page → `key code 116` (PREFERRED for browsing)
- **Down arrow**: Scroll line-by-line → `key code 125` (use for fine control)
- **Up arrow**: Scroll up line-by-line → `key code 126`
- **Cmd+T**: New tab → `keystroke "t" using command down`
- **Cmd+W**: Close tab → `keystroke "w" using command down`

### Text Entry
- `keystroke "text to type"` = Type literal text
- `keystroke "search query"` = Type search query

### App Control
- `open -a "Google Chrome"` = Launch Chrome (Bash)
- `tell application "Google Chrome" to activate` = Focus Chrome

## Real Examples

### Example 1: Search LinkedIn for Topic

```bash
# Focus Chrome
osascript -e 'tell application "Google Chrome" to activate'

# Navigate to LinkedIn search
osascript -e 'tell application "System Events" to keystroke "l" using command down'
osascript -e 'tell application "System Events" to keystroke "https://www.linkedin.com/search/results/content/?keywords=ai%20consciousness"'
osascript -e 'tell application "System Events" to key code 36'

# Wait for load
sleep 4

# Scroll one page at a time with Page Down
osascript -e 'tell application "System Events" to key code 121'
sleep 2

# Capture results
screencapture -x /tmp/linkedin_results.png
```

## HOW IT WORKS: AX + osascript = Perfect User Impersonation

### The Pipeline:
1. **Screenshot** - See what's on screen
2. **ax_executor searches** - Find element by visible label (what you see)
3. **osascript clicks/types** - Perform the action exactly as you would
4. **Screenshot verifies** - Confirm it worked
5. **Repeat** - Until goal achieved

### Step 1: Take Screenshot

```bash
screencapture -x /tmp/state.png
# See what's currently on screen
```

### Step 2: Find Element by Its Label

```bash
python3 ~/.claude/skills/ax-executor/ax_executor_skill.py "Login Button"
# Returns: Found! Role: AXButton, Label: "Login Button", Position: (234, 456)
```

The AX framework searches for elements the same way accessibility features do - by their visible labels.

### Step 3: Click It

```bash
python3 ~/.claude/skills/ax-executor/ax_executor_skill.py "Login Button" --click
# Clicks the button at the coordinates AX returned
# Exactly like you clicking it with your mouse
```

### Step 4: Verify

```bash
screencapture -x /tmp/state_after.png
# Confirm the action worked
```

## Key Principle: Division of Labor

| Mode | Who | Speed | Visibility | Interaction |
|------|-----|-------|------------|-------------|
| HEADLESS | Me | 3-5s | No window | Automatic extraction |
| UI | You | Manual | Full screen | Point & click |

## Why osascript Works Better Than AX Framework

| Aspect | osascript | AX Framework |
|--------|-----------|--------------|
| Dynamic content | Works (keyboard is universal) | Struggles with DOM changes |
| Frame info | Not needed | Required to click |
| Speed | Fast (direct keyboard) | Slow (DOM parsing) |
| Dependencies | Built-in to macOS | Needs pyautogui (can be missing) |
| Reliability | High (browser shortcut keys) | Variable (depends on element structure) |

## When to Use This Skill

✅ **Use chrome-control for**:
- Navigating to URLs
- Searching websites
- Scrolling to discover content
- Taking screenshots of pages
- Following links via keyboard (Tab + Enter)
- Multi-step navigation workflows

❌ **Don't use for**:
- Complex form filling with many fields
- Precise coordinate-based interactions
- Dragging/dropping elements
- Typing special characters that don't translate well

## Key Insights

1. **Navigate directly**: Use Cmd+L to focus address bar and type full URLs
2. **Search via URL parameters**: When possible, build search URLs directly (faster than UI search)
3. **Wait is critical**: Always `sleep 3-4` after navigation for page load
4. **Screenshot verifies**: Always capture before/after to confirm page state
5. **Keyboard is universal**: Works on any website without needing DOM knowledge
6. **Use Page Down for browsing**: `key code 121` (Page Down) scrolls one full page - much more efficient than multiple arrow key presses
7. **Use arrow keys for fine control**: `key code 125` (Down) for line-by-line scrolling when you need precision

## Troubleshooting

### Page not loading after Enter
- Increase sleep time: `sleep 5` instead of `sleep 3`
- Check URL syntax - some characters need escaping

### Screenshot is blank or incomplete
- Wait longer after navigation: `sleep 4-5`
- Page might require interaction before rendering

### Tab navigation not working
- Some sites override Tab behavior
- Try Cmd+Option+Right arrow for next tab instead

## Related Skills

- **ax-executor**: For clicking specific UI elements when you know their labels
- **context-rag**: For researching topics found via Chrome navigation
