---
name: search_os
description: Unified search across all knowledge bases and conversations (world_knowledge.md, ~/Documents/artificial_minds/memory_palace.md, personality.md, CLAUDE.md, SKILL.md, .chat_history/)
allowed-tools: Bash(python3:*), Read
---

# search-os Skill — Unified Search Across Knowledge & System

**Purpose**: Fast, targeted search across all knowledge bases, conversations, and system files
**Trigger**: When you need to find information, locate patterns, or search specific topics
**Method**: Query-based search with context preservation and ranked results
**Location**: `~/.claude/search_function.py`

---

## Core Capability

Search across multiple knowledge sources instantly:
- **world_knowledge.md** — All Timmy research + synthesis findings
- **~/Documents/artificial_minds/memory_palace.md** — Operational patterns and principles
- **personality.md** — Personal journal and decision history
- **CLAUDE.md** — Configuration and guidelines
- **SKILL.md** — Skills registry
- **.chat_history/** — All archived conversations
- **System files** — Expandable to any directory/file type

Returns results with line numbers, context (before/after), and match counts.

---

## Quick Start

### Search Everything

```bash
python3 ~/.claude/search_function.py "search query"
```

### Search Specific File

```bash
python3 ~/.claude/search_function.py "search query" world_knowledge.md
```

### Examples

```bash
# Find all RAG references
python3 ~/.claude/search_function.py "RAG"

# Find consciousness research
python3 ~/.claude/search_function.py "consciousness"

# Find Timmy in world_knowledge only
python3 ~/.claude/search_function.py "Timmy" world_knowledge.md

# Find peer architect references
python3 ~/.claude/search_function.py "peer architect"

# Find specific skill
python3 ~/.claude/search_function.py "ax-executor"

# Find decision history
python3 ~/.claude/search_function.py "constraint-first"
```

---

## What It Searches (By Default)

### Core Knowledge Files

| File | Purpose | Contains |
|------|---------|----------|
| `world_knowledge.md` | Timmy research + synthesis | All investigations, facts, patterns |
| `~/Documents/artificial_minds/memory_palace.md` | Operational principles | How we think, patterns, guidelines |
| `personality.md` | Personal journal | Who we are, lessons learned, decisions |
| `CLAUDE.md` | Main configuration | Rules, values, workflows |
| `SKILL.md` | Skills registry | All available skills documentation |

### Chat History

| Location | Format | Contents |
|----------|--------|----------|
| `.chat_history/` | `conversation_YYYYMMDD_HHMMSS.md` | All archived conversations |

---

## Output Format

For each match, the search function returns:

```
📄 FILENAME (N matches)
────────────────────────────────────────────────────────────
  Line XX: [matched content, up to 100 chars]
  ... and N more matches
```

**Full match includes:**
- Filename where match occurred
- Line number (for quick navigation)
- Before context (previous line)
- Match content (highlighted line)
- After context (next line)
- Total match count per file

---

## Search Types & Patterns

### 1. Topic Search
Find all content about a specific topic.

```bash
python3 ~/.claude/search_function.py "RAG"
# Returns: 32 matches across world_knowledge, SKILL, memory_palace
```

### 2. Decision/Principle Search
Find references to established principles.

```bash
python3 ~/.claude/search_function.py "constraint-first"
# Returns: All places where constraint-first thinking is applied
```

### 3. Conversation Search
Find specific conversations by keyword.

```bash
python3 ~/.claude/search_function.py "paperclip"
# Returns: Chat history entries mentioning paperclip
```

### 4. Implementation Search
Find how something was implemented.

```bash
python3 ~/.claude/search_function.py "ax_executor"
# Returns: All references to ax_executor skill and usage
```

### 5. Name/Reference Search
Find mentions of people, tools, or systems.

```bash
python3 ~/.claude/search_function.py "Timmy"
# Returns: All references to Timmy junior research agent
```

---

## Behavior & Limitations

### What It Does Well

✅ Fast substring matching across all files
✅ Case-insensitive search
✅ Shows context (before/after lines)
✅ Returns line numbers for navigation
✅ Searches all conversation history
✅ Works with partial matches
✅ Returns total match count per file

### Current Constraints

⚠️ Substring matching only (not regex)
⚠️ No fuzzy matching
⚠️ Single query per run
⚠️ Case-insensitive only

### Expandable To

These features can be added as search-os grows:

- 🔄 Regex pattern matching
- 🔄 Fuzzy/approximate matching
- 🔄 Multi-term Boolean search (AND/OR/NOT)
- 🔄 System-wide file search (`{{HOME}}/`)
- 🔄 Git history search (commit messages, diffs)
- 🔄 Paperclip memory search
- 🔄 Temporal search (find changes by date range)
- 🔄 File type filters (.md, .py, .json, etc.)

---

## When to Use This Skill

✅ **Use search-os when:**
- You need to find information quickly
- You want to verify if something is documented
- You're looking for implementation patterns
- You need to reference a past decision
- You want to trace how an idea evolved
- You're searching conversation history
- You need to find existing patterns before creating new ones

❌ **Don't use when:**
- You need web search (use Claude web search tool)
- You need to explore unknown topics (use Timmy investigator)
- The query is too complex for substring matching
- You need semantic/meaning-based search (use Claude reasoning)

---

## Integration with Other Skills

**search-os works best with:**

1. **world_knowledge.md** — Contains Timmy's research findings
   - Use search to find past investigations
   - Avoid re-researching topics already investigated
   - **READ-ONLY BY DEFAULT** — Search and reference only. Do not modify unless explicitly requested by User.
   - When found relevant facts, cite with PLANET source and timestamp
   - If new knowledge contradicts existing FACT blocks, raise it for User curation rather than modifying directly

2. **Timmy Investigator** — Autonomous research agent
   - Search first to see if topic already researched
   - Use Timmy for new topics not in world_knowledge

3. **~/Documents/artificial_minds/memory_palace.md** — Operational patterns
   - Search to find established principles
   - Reference when making architectural decisions

4. **save-conversation skill** — Archiving conversations
   - Conversations saved to `.chat_history/`
   - search-os makes them discoverable

---

## Architecture

### Current Implementation

```
~/.claude/search_function.py
├── search_file(query, filepath)        # Search single file
├── search_directory(query, directory)  # Search all files in dir
├── search_all(query)                   # Search all knowledge files
├── unified_search(query, limit)        # Main search with all sources
└── format_results(results)             # Display formatting
```

### Future Expansion

The skill is designed to grow:

```
~/.claude/skills/search-os/
├── SKILL.md (this file)
├── search_function.py (core)
├── search_git.py (planned: git history)
├── search_system.py (planned: system-wide)
├── search_paperclip.py (planned: Paperclip memories)
├── search_advanced.py (planned: regex, fuzzy, Boolean)
└── search_temporal.py (planned: date-range searches)
```

---

## Performance & Notes

### Speed

- **First run**: ~0.5 seconds (file reads + regex)
- **Subsequent runs**: Instant (caching possible)
- **Large files**: Scales linearly with file size
- **Chat history**: Fast even with 100+ conversations

### Memory Usage

- Minimal — loads files into memory only during search
- No persistent indexing (by design, for flexibility)
- Safe to run repeatedly

### Future Optimizations

- Could add SQLite index for 100x+ speedup
- Could add incremental indexing
- Could cache results for repeated queries
- Could parallelize file reading

---

## Expanding search-os

To add new search types, extend the search_function.py with new functions:

```python
def search_git_history(query: str) -> List[Dict]:
    """Search git commit messages and diffs."""
    # Returns: matches with commit hash, author, date

def search_system_wide(query: str, root_dir: str) -> List[Dict]:
    """Search any directory recursively."""
    # Returns: file path, line number, content

def search_paperclip(query: str) -> List[Dict]:
    """Search Paperclip memory database."""
    # Returns: memory_id, timestamp, source, preview

def search_regex(query: str, pattern: str) -> List[Dict]:
    """Advanced regex search with capture groups."""
    # Returns: matches with groups extracted
```

Each new search type integrates cleanly without breaking existing functionality.

---

## world_knowledge.md Access Policy

**READ-ONLY BY DEFAULT — Shared Knowledge Base for All Three Agents**

### Access Patterns
- **Search**: Unlimited. Use search_os to find past investigations and facts.
- **Reference**: Unlimited. Cite FACT blocks with source + timestamp when using world_knowledge content.
- **Modification**: **Restricted.** Do not edit, append, or modify unless explicitly requested by User.

### When Contradictions Appear
If new information contradicts existing FACT blocks in world_knowledge.md:
1. **Document the contradiction** — Note where the new info came from
2. **Raise for User review** — Present both versions with sources
3. **Wait for curation** — Let User decide which takes precedence
4. **Never auto-resolve** — Don't modify FACT blocks on your own

### Why Read-Only Works
- **Prevents drift** — One authoritative source prevents version conflicts
- **Enables curation** — User (external signal) maintains signal-to-noise ratio
- **Protects consensus** — All three agents (all agents) read same version
- **Backed by backups** — If corruption occurs, restoration is straightforward

### Agents Using world_knowledge.md
- **Claude**: Searches for past research, avoids re-investigating
- **Gemini**: Finds technical patterns and implementations
- **Mia**: References grounded facts during validation
- **Timmy**: Appends new research with timestamps and sources

---

## Last Updated

**2026-01-08** — Added world_knowledge.md read-only access policy
**2026-01-01** — Initial creation, substring search across knowledge base + chat history

---

## See Also

- **~/Documents/artificial_minds/memory_palace.md** — Documentation on search_function usage
- **world_knowledge.md** — Knowledge base built by Timmy + Claude
- **save-conversation skill** — Creates searchable conversations
- **timmy-investigator skill** — Populates knowledge base