# Mission: Upgrade Claude Code Configuration (Safe Merge)

You are tasked with upgrading the user's local Claude Code environment using the configuration files in this repository.

**Constraint: NO DESTRUCTIVE ACTIONS.**
Do not overwrite existing files without creating a timestamped backup first.

## Phase 1: Analysis & Backup
1. **Analyze** the user's existing `~/.claude/` directory.
   - Does `~/.claude/CLAUDE.md` exist?
   - Does `~/.claude/skills/` exist?
2. **Create Backup**:
   - If existing config is found, create a backup directory: `~/.claude_backup_[TIMESTAMP]/`
   - Copy all current contents of `~/.claude/` into that backup.
   - Report the backup location to the user.

## Phase 2: Intelligent Merge
1. **Skills**:
   - Copy the new skills from `skills/` to `~/.claude/skills/`.
   - If a skill already exists (e.g., `ax-executor`), ask the user if they want to **upgrade** it (replace) or **keep** their version.
2. **Scripts**:
   - Copy `scripts/contextrag.py` and `scripts/contextzip.py` to `~/.claude/`.
3. **Configuration (CLAUDE.md)**:
   - **Do NOT overwrite `CLAUDE.md`.**
   - Instead, read `config/CLAUDE.md.template`.
   - Identify the "Key Locations" and "System Rules" sections.
   - Append these new sections to the user's existing `CLAUDE.md` if they are missing.
4. **Knowledge Base**:
   - Check if `~/Documents/artificial_minds/` exists.
   - If not, create it and copy `knowledge/memory_palace.md.template` there (renaming to `memory_palace.md`).
   - If it *does* exist, do not touch `memory_palace.md`. Instead, create `memory_palace.new.md` and let the user decide.

## Phase 3: Environment Setup
1. **Virtual Environment**:
   - Check if `~/.claude/.venv` exists.
   - If not, create it: `python3 -m venv ~/.claude/.venv`
2. **Dependencies**:
   - Install the requirements from `requirements.txt` into that venv.
   - Command: `~/.claude/.venv/bin/pip install -r requirements.txt`

## Phase 4: Verification
1. Run a quick check to see if `ax-executor` and `context-rag` are recognized.
2. Print a success message summarizing what was added and where the backups are.

**Start this mission by analyzing the current ~/.claude structure.**
