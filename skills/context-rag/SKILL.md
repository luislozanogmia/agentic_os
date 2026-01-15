---
name: context-rag
description: Use knowledge retrieval to bring context from web research or local knowledge into responses. Use when discussing complex topics or referencing established principles in your knowledge base.
allowed-tools: Bash(python3:*), Read, Grep
---

# Context RAG Skill

## What This Is
This skill provides tools for retrieving and injecting relevant context into your reasoning process.

## Local Knowledge Search
Use `search_function.py` to find relevant sections in your memory palace or world knowledge base.

```bash
python3 scripts/search_function.py "your query"
```

## Responsibilities
- **Search**: Look for existing knowledge before performing new research.
- **Inject**: Format findings for natural integration into responses.
- **Validate**: Ensure retrieved content is relevant and up-to-date.

## Key Files
- `scripts/search_function.py`: Core search logic.
- `scripts/inject_context.py`: Formatting and injection helper.
- `scripts/validate_context.py`: Structural and safety validation.
