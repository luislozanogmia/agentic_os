#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Claude Code Config Installer${NC}"

echo -e "${YELLOW}⚠️  WARNING: This script will OVERWRITE your existing ~/.claude configuration!${NC}"
echo "If you have an existing setup and want to keep your data, STOP NOW."
echo "Instead, use Claude Code to intelligently merge the configs:"
echo -e "${GREEN}   claude -p setup.md${NC}"

if [[ "$1" != "--yolo" && "$1" != "--force" ]]; then
    read -p "Press [Enter] to overwrite and install fresh, or Ctrl+C to cancel..."
else
    echo -e "${GREEN}🤘 YOLO MODE ENGAGED: Overwriting configurations...${NC}"
fi

# 1. Platform Detection
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}Error: setup.sh is for macOS.${NC}"
    echo "For Windows, run setup.ps1 from PowerShell."
    exit 1
fi

# 2. Path Setup
CLAUDE_HOME="${HOME}/.claude"
DOCS_PATH="${HOME}/Documents/artificial_minds"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "  Target: ${CLAUDE_HOME}"
echo "  Knowledge Base: ${DOCS_PATH}"

# 3. Create Structure
mkdir -p "${CLAUDE_HOME}"/{skills,.chat_history}
mkdir -p "${DOCS_PATH}"

# 4. Copy Skills & Scripts
echo "📦 Copying modules..."
cp -r "${REPO_ROOT}/skills/"* "${CLAUDE_HOME}/skills/" 2>/dev/null || true
cp "${REPO_ROOT}/scripts/"*.py "${CLAUDE_HOME}/" 2>/dev/null || true

# 5. Process Templates
echo "⚙️ Configuring templates..."
# Process Markdown templates
sed "s|{{CLAUDE_HOME}}|${CLAUDE_HOME}|g; s|{{DOCS_PATH}}|${DOCS_PATH}|g; s|{{HOME}}|${HOME}|g" \
    "${REPO_ROOT}/config/CLAUDE.md.template" > "${CLAUDE_HOME}/CLAUDE.md"

cp "${REPO_ROOT}/config/SKILL.md" "${CLAUDE_HOME}/SKILL.md"

sed "s|{{CLAUDE_HOME}}|${CLAUDE_HOME}|g; s|{{DOCS_PATH}}|${DOCS_PATH}|g; s|{{HOME}}|${HOME}|g" \
    "${REPO_ROOT}/knowledge/memory_palace.md.template" > "${DOCS_PATH}/memory_palace.md"

cp "${REPO_ROOT}/knowledge/world_knowledge.md.template" "${DOCS_PATH}/world_knowledge.md"

# Process Python placeholders in the installed files
find "${CLAUDE_HOME}" -name "*.py" -exec sed -i "" "s|{{CLAUDE_HOME}}|${CLAUDE_HOME}|g" {} + # Note: macOS sed requires an argument for -i, even if empty.

# 6. Setup Virtual Environment
echo "🐍 Setting up Python environment..."
python3 -m venv "${CLAUDE_HOME}/.venv"
source "${CLAUDE_HOME}/.venv/bin/activate"
pip install --upgrade pip
pip install -r "${REPO_ROOT}/requirements.txt"

# 7. LaunchAgents (optional)
echo ""
read -p "Install LaunchAgents for automation (backup, auto-save)? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    mkdir -p "${HOME}/Library/LaunchAgents"
    for plist in "${REPO_ROOT}/launchagents/"*.plist.template; do
        filename=$(basename "$plist" .template)
        sed "s|{{CLAUDE_HOME}}|${CLAUDE_HOME}|g; s|{{HOME}}|${HOME}|g" \
            "$plist" > "${HOME}/Library/LaunchAgents/${filename}"
        launchctl unload "${HOME}/Library/LaunchAgents/${filename}" 2>/dev/null || true
        launchctl load "${HOME}/Library/LaunchAgents/${filename}"
    done
    echo -e "${GREEN}✅ LaunchAgents installed and loaded${NC}"
fi

echo -e "\n${GREEN}✅ Installation Complete!${NC}"
if [ ! -f "${CLAUDE_HOME}/.env" ]; then
    echo "GROQ_API_KEY=" > "${CLAUDE_HOME}/.env"
    echo "OPENAI_API_KEY=" >> "${CLAUDE_HOME}/.env"
    echo -e "${YELLOW}⚠️  Created empty .env file at ${CLAUDE_HOME}/.env${NC}"
    echo -e "${YELLOW}👉 Please add your API keys there for full functionality.${NC}"
fi

if [[ -f "${REPO_ROOT}/skills/bot-bridge/setup_bot_env.sh" ]]; then
    echo ""
    read -p "Configure $HOME/bot.env for bot-bridge now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        /bin/bash "${REPO_ROOT}/skills/bot-bridge/setup_bot_env.sh"
    fi
fi


echo "Restart Claude Code to apply changes."
