# Dependencies

The Python environment is managed automatically by `setup.sh` in `~/.claude/.venv`.

## Core Python Packages
- **requests**: For web RAG and API calls.
- **beautifulsoup4**: For HTML parsing.
- **pyperclip**: For clipboard operations (used in "impersonation" mode).
- **python-dotenv**: For loading API keys from `.env`.

## macOS Frameworks (PyObjC)
- **pyobjc-framework-Accessibility**: Access to the AX tree.
- **pyobjc-framework-Cocoa**: AppKit and Foundation bridges.
- **pyobjc-framework-Quartz**: CoreGraphics for mouse/keyboard control.

## External APIs
- **Groq**: Recommended for swarm worker completions.
- **OpenAI**: Optional fallback.
- **Any OpenAI-compatible endpoint**: Supported by `skills/bot-bridge/bot_bridge.py` via `BOT_LLM_BASE_URL`.
