#!/bin/bash
set -euo pipefail

# Only run in cloud/remote environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Install cloud-compatible Python dependencies
# Skip pyobjc packages (macOS-only) by installing individually
pip install --quiet \
  "requests>=2.32.0" \
  "beautifulsoup4>=4.13.0" \
  "pyperclip>=1.9.0" \
  "python-dotenv>=1.1.0"

# Make scripts executable
chmod +x "$CLAUDE_PROJECT_DIR"/scripts/*.py 2>/dev/null || true
