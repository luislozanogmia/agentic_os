# Architecture Overview

This configuration implements a **Reflection-First** architecture for autonomous agents.

## Core Layers

### 1. The Skill Layer
Specialized Python scripts and Markdown instructions that teach Claude how to use system-level tools. These live in `~/.claude/skills/`.

### 2. The Grounding Layer (Memory)
Persistent knowledge bases (`world_knowledge.md`, `memory_palace.md`) that ensure Claude remembers your preferences, research, and operating patterns across sessions.

### 3. The Execution Layer
Deterministic automation via `ax-executor` and `osascript`. Instead of "hallucinating" how to interact with an app, Claude searches for the actual UI elements.

### 4. The Validation Layer
The "Two Worlds" principle: AI-native operations (search, bash, files) are preferred over UI-based ones. Every action should be verifiable via screenshots or log checks.

## Tool Priority Hierarchy
1. **Registered Skills** (High-level abstraction)
2. **Pre-built Scripts** (Optimized utilities)
3. **Specialized Tools** (Precise file ops)
4. **Raw Bash** (Fallback)
