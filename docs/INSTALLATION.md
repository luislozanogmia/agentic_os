# Installation Guide

## Prerequisites
- **macOS**: This configuration uses macOS-specific APIs (AppleScript, CoreGraphics, Accessibility).
- **Python 3.10+**: Required for the automation scripts.
- **Claude Code CLI**: Make sure you have the official `claude` CLI installed.

## Quick Install
1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/claude-code-config.git
   cd claude-code-config
   ```

2. **Run the setup script**:
   ```bash
   ./setup.sh
   ```
   *Note: If you have an existing config, use `./setup.sh --yolo` to force overwrite or follow the instructions in `setup.md` for a safe merge.*

3. **Configure API Keys**:
   Open `~/.claude/.env` and add your keys:
   ```env
   GROQ_API_KEY=sk_...
   OPENAI_API_KEY=sk_...
   ```

4. **Grant Permissions**:
   - Go to **System Settings > Privacy & Security > Accessibility**.
   - Add your **Terminal** app (or VS Code) to the list.
   - Go to **Input Monitoring** and do the same.

## Verifying the Setup
Restart your terminal and run:
```bash
claude
```
Then try typing `/help` to see the newly installed skills.
