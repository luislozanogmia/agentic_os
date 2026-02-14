#!/usr/bin/env python3
"""
W08 World Knowledge Worker - Unified Research & Librarian
Uses OpenRouter (Nemotron 30B free) for research + Groq (Kimi K2) for KB reorganization.

Usage:
    python3 W08_world_knowledge.py investigate "topic"   # Research + append + reorganize
    python3 W08_world_knowledge.py fix                   # Just reorganize KB
    python3 W08_world_knowledge.py batch "t1" "t2" ...   # Multiple topics
"""

import os
import sys
import re
import json
import time
import asyncio
import hashlib
import datetime
import subprocess
import tempfile
import requests
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple

# --- Configuration ---
HOME = Path.home()
WORLD_KNOWLEDGE_PATH = HOME / "Documents" / "artificial_minds" / "world_knowledge.md"

# API Endpoints
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Models
RESEARCH_MODEL = "nvidia/nemotron-3-nano-30b-a3b:free"  # Free tier on OpenRouter
LIBRARIAN_MODEL = "moonshotai/kimi-k2-instruct-0905"    # Kimi K2 on Groq

# --- Load Environment ---
def load_env() -> Dict[str, str]:
    result = {}
    env_files = [
        Path("{{CLAUDE_HOME}}/.env"),
        Path("{{CLAUDE_HOME}}/.env")
    ]
    for env_file in env_files:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    result[k.strip()] = v.strip().strip('"').strip("'")
    return result

ENV = load_env()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or ENV.get("OPENROUTER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or ENV.get("GROQ_API_KEY", "")

# --- State Management ---
class WorkerState:
    def __init__(self):
        self.seed: Optional[str] = None
        self.context: str = ""
        self.chat_history: List[tuple] = []
        self.previous_searches: List[str] = []
        self.fact_history: Set[str] = set()
        self.recent_facts: List[str] = []
        self.cycle_count: int = 0

state = WorkerState()

# --- OpenRouter API Call (Nemotron 30B) ---
def call_openrouter(messages: List[Dict], max_tokens: int = 2000, retry: int = 0) -> str:
    """Call OpenRouter API with Nemotron 30B free model."""
    if not OPENROUTER_API_KEY:
        print("OPENROUTER_API_KEY not found", file=sys.stderr)
        return ""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://example.com"),
        "X-Title": "W08 World Knowledge Worker"
    }

    payload = {
        "model": RESEARCH_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens
    }

    try:
        resp = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        try:
            content = data["choices"][0]["message"].get("content", "")
        except (KeyError, IndexError, AttributeError):
            content = ""

        if not content:
            preview = json.dumps(data)[:200]
            print(f"OpenRouter empty response ({preview})", file=sys.stderr)
            return ""

        return content.strip()
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 429 and retry < 3:
            wait = 2 ** (retry + 1)
            print(f"Rate limited, waiting {wait}s...", file=sys.stderr)
            time.sleep(wait)
            return call_openrouter(messages, max_tokens, retry + 1)
        print(f"OpenRouter error: {e}", file=sys.stderr)
        if hasattr(resp, 'text'):
            print(f"Response: {resp.text[:200]}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"OpenRouter error: {e}", file=sys.stderr)
        return ""

# --- Generate Text (via OpenRouter) ---
def generate_text(prompt: str, max_tokens: int = 2000) -> str:
    """Generate text using Nemotron 30B via OpenRouter."""
    messages = [{"role": "user", "content": prompt}]

    print("Calling Nemotron 30B...", end=" ", flush=True)
    response = call_openrouter(messages, max_tokens)

    if response:
        print("Done.")
        # Clean up any thinking tags
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
        response = response.replace("</think>", "").strip()
    else:
        print("Failed.")

    return response

# --- Prompt Builders ---
def build_system_prompt(seed: str) -> str:
    today = datetime.datetime.now().strftime("%b %d %Y")
    return f"Date: {today}\nRole: Research assistant\nTopic: {seed}\n"

def build_research_prompt(question: str, seed: Optional[str], facts: List[str]) -> str:
    today = datetime.datetime.now().strftime("%b %d %Y")
    fact_block = "Known facts:\n" + "\n".join(f"- {f}" for f in facts) + "\n\n" if facts else ""
    seed_line = f"Research focus: {seed}\n" if seed else ""

    return f"""You are W08, a research assistant. Today is {today}.

{seed_line}{fact_block}
Research question: {question}

Instructions:
1. Analyze the question and any provided facts
2. Provide a concise, structured response (6-10 sentences)
3. At the end, suggest exactly 2 follow-up searches in this format:
   NEXT SEARCH 1: <specific search query>
   NEXT SEARCH 2: <specific search query>

Your response:"""

def build_meta_prompt(seed: str, facts: List[str], qa_history: str) -> str:
    fact_block = "Recent facts:\n" + "\n".join(f"- {f}" for f in facts) + "\n" if facts else ""

    return f"""You are W08, reflecting on research progress.

Topic: {seed}
{fact_block}
Recent Q&A:
{qa_history}

Based on the above, can you CONCLUDE your research, or do you NEED FURTHER INFORMATION?

If you can conclude, write: CONCLUDE: <brief reason>
If you need more info, write: NEED FURTHER INFORMATION and suggest 2 search queries.

Your decision:"""

# --- RAG (Web Search) ---
def run_rag(query: str) -> List[str]:
    """Run contextrag for web search facts."""
    try:
        contextrag_path = HOME / ".claude" / "contextrag.py"

        if not contextrag_path.exists():
            print(f"contextrag.py not found at {contextrag_path}", file=sys.stderr)
            return []

        # Ingest
        subprocess.run(
            ["python3", str(contextrag_path), "ingest", query, "--top", "2"],
            capture_output=True, timeout=20
        )

        # Compose
        result = subprocess.run(
            ["python3", str(contextrag_path), "compose", query, "--min-needed", "1"],
            capture_output=True, text=True, timeout=15
        )

        facts = []
        for line in result.stdout.splitlines():
            s = line.strip()
            if s.startswith("- [") and len(s) > 30:
                facts.append(s)

        return facts[:3] if facts else []
    except subprocess.TimeoutExpired:
        print(f"RAG timeout for: {query}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"RAG error: {e}", file=sys.stderr)
        return []

# --- Reasoning Cycle ---
def hash_fact(fact: str) -> str:
    return hashlib.sha256(fact.encode()).hexdigest()

def reasoning_cycle(question: str) -> tuple:
    """Single reasoning cycle with RAG + Nemotron."""
    # Get facts from web search
    print(f"Searching: {question[:50]}...")
    facts = run_rag(question)
    if facts:
        print(f"Found {len(facts)} fact(s)")

    # Build prompt and generate
    prompt = build_research_prompt(question, state.seed, facts)
    print("\nW08: ", end="")
    answer = generate_text(prompt, max_tokens=1500)

    if answer:
        print(f"\n{answer}\n")

    # Extract next searches
    searches = re.findall(r'NEXT SEARCH\s*[12]\s*:\s*(.+)', answer, re.IGNORECASE)
    unique_searches = []
    for s in searches:
        clean = s.strip().lower()
        if not any(clean in ps or ps in clean for ps in state.previous_searches):
            unique_searches.append(s.strip())
            state.previous_searches.append(clean)
    state.previous_searches = state.previous_searches[-10:]

    # Store facts
    for f in facts:
        h = hash_fact(f)
        if h not in state.fact_history:
            state.fact_history.add(h)
            state.context += f"[FACT]: {f}\n"

    state.chat_history.append((question, answer))
    state.context += f"\nQ: {question}\nA: {answer}\n"

    return answer, unique_searches

# --- Meta Reflection ---
def meta_reflect() -> str:
    """Decide whether to conclude or continue research."""
    fact_matches = re.findall(r'\[FACT]: ([^\]]+)\]', state.context)
    recent_facts = fact_matches[-5:] if fact_matches else []

    qa_block = ""
    for i, (q, a) in enumerate(state.chat_history[-3:]):
        qa_block += f"Q{i+1}: {q}\nA{i+1}: {a[:300]}...\n"

    prompt = build_meta_prompt(state.seed, recent_facts, qa_block)
    output = generate_text(prompt, max_tokens=300)

    if re.search(r'\bCONCLUDE\b', output, re.IGNORECASE):
        return "conclude"
    elif re.search(r'NEED FURTHER INFORMATION', output, re.IGNORECASE):
        return "need_more"
    return "undecided"

# --- Final Summary Generation ---
def generate_final_summary(topic: str) -> str:
    """Generate a 15-line summary synthesizing all research."""
    # Collect RAG facts
    rag_facts = []
    for line in state.context.split('\n'):
        if '[FACT]:' in line and 'PRESENT' in line:
            rag_facts.append(line.strip())

    # Collect reasoning from Q&A (remove NEXT SEARCH noise)
    reasoning = ""
    for i, (q, a) in enumerate(state.chat_history):
        clean_a = re.sub(r'NEXT SEARCH.*', '', a, flags=re.IGNORECASE).strip()
        reasoning += f"--- Cycle {i+1} ---\n{clean_a[:600]}\n\n"

    facts_block = "\n".join(rag_facts[:5]) if rag_facts else "No web facts collected."

    prompt = f"""Synthesize research on: {topic}

Web Facts:
{facts_block}

Reasoning:
{reasoning}

Write exactly 15 lines summarizing:
- What this is (1-2 lines)
- Key technical details (4-5 lines)
- Performance/benchmarks (2-3 lines)
- Practical implications (2-3 lines)
- Open questions (1-2 lines)

Be factual and dense. No intro phrases like "This research..." - just facts."""

    print("Generating final summary...")
    summary = generate_text(prompt, max_tokens=600)
    summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL).strip()
    return summary

# --- Daily Report Helpers ---
def extract_recent_entries(limit: int = 5) -> List[Tuple[str, str]]:
    if not WORLD_KNOWLEDGE_PATH.exists():
        return []

    entries: List[Tuple[str, str]] = []
    title: Optional[str] = None
    buffer: List[str] = []

    for line in WORLD_KNOWLEDGE_PATH.read_text().splitlines():
        if line.startswith("## "):
            if title and buffer:
                entries.append((title, "\n".join(buffer).strip()))
            title = line[3:].strip()
            buffer = []
        elif title:
            buffer.append(line)

    if title and buffer:
        entries.append((title, "\n".join(buffer).strip()))

    return entries[-limit:]


def build_report(entries: List[Tuple[str, str]]) -> str:
    timestamp = datetime.datetime.now().strftime("%B %d, %Y %H:%M %Z")
    if not entries:
        return f"W08 Daily Investigation Summary\nGenerated: {timestamp}\n\nNo entries were found in world_knowledge.md."

    report_lines = [
        "W08 Daily Investigation Summary",
        f"Generated: {timestamp}",
        "",
    ]

    for title, body in entries:
        trimmed = body.split("**Sources:**")[0].strip()
        report_lines.append(f"### {title}")
        report_lines.append(trimmed)
        report_lines.append("")

    report_lines.append("— W08 World Knowledge Worker")
    return "\n".join(report_lines).strip()


def send_mail(recipient: str, subject: str, body: str) -> bool:
    script = """on run argv
set recipientAddress to item 1 of argv
set subjectText to item 2 of argv
set bodyText to item 3 of argv
tell application \"Mail\"
    set newMessage to make new outgoing message with properties {subject:subjectText, content:bodyText & "\n"}
    tell newMessage
        make new to recipient at end of to recipients with properties {address:recipientAddress}
        send
    end tell
end tell
end run
"""

    with tempfile.NamedTemporaryFile("w", suffix=".applescript", delete=False) as tmp:
        tmp.write(script)
        script_path = tmp.name

    try:
        subprocess.run(["osascript", script_path, recipient, subject, body], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Email send failed: {e}", file=sys.stderr)
        return False
    finally:
        try:
            os.remove(script_path)
        except OSError:
            pass


def email_daily_report(recipient: str, limit: int = 5):
    entries = extract_recent_entries(limit=limit)
    body = build_report(entries)
    subject = "W08 Daily Investigation Summary"
    if send_mail(recipient, subject, body):
        print(f"Sent daily report to {recipient}")
    else:
        print("Failed to send report", file=sys.stderr)

# --- World Knowledge Append ---
def append_to_world_knowledge(topic: str, summary: str):
    """Append research summary to world_knowledge.md."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp_readable = datetime.datetime.now().strftime("%b %d, %Y")

    if not WORLD_KNOWLEDGE_PATH.exists():
        WORLD_KNOWLEDGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        WORLD_KNOWLEDGE_PATH.write_text("# World Knowledge Base\n*Built by W08*\n\n---\n\n")

    # Extract clean RAG sources
    sources = []
    for line in state.context.split('\n'):
        if '[FACT]:' in line and 'PRESENT' in line:
            # Clean: remove [FACT]: - [PRESENT] prefix, keep content and URL
            clean = re.sub(r'\[FACT\]:\s*-?\s*\[PRESENT\]\s*', '', line).strip()
            if clean:
                sources.append(f"- {clean[:200]}")

    sources_block = "\n".join(sources[:3]) if sources else "- No web sources"

    entry = f"""## {topic}
**Discovered:** {timestamp}

{summary}

**Sources:**
{sources_block}

*Timestamp {timestamp_readable}*

---

"""
    with open(WORLD_KNOWLEDGE_PATH, 'a') as f:
        f.write(entry)

    print(f"Added to world_knowledge.md")

# --- Librarian (Kimi K2 on Groq) ---
class Librarian:
    """Reorganize KB using Kimi K2 via Groq API."""

    def call_kimi(self, prompt: str, max_tokens: int = 8192, retry: int = 0) -> str:
        if not GROQ_API_KEY:
            raise SystemExit(f"GROQ_API_KEY not found. Please set it in {ENV_PATH}")
            return ""

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": LIBRARIAN_MODEL,
            "messages": [
                {"role": "system", "content": "You are a knowledge librarian. Reorganize using Cluster > Galaxy > Sun > Fact hierarchy. Return ONLY the reorganized markdown."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": max_tokens
        }

        try:
            resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=None)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429 and retry < 3:
                time.sleep(2 ** (retry + 1))
                return self.call_kimi(prompt, max_tokens, retry + 1)
            print(f"Kimi API error: {e}", file=sys.stderr)
            return ""
        except Exception as e:
            print(f"Kimi error: {e}", file=sys.stderr)
            return ""

    def validate(self, original: str, reorganized: str) -> bool:
        if not original or not reorganized:
            return False

        ratio = len(reorganized) / len(original)
        if ratio < 0.95:
            print(f"Validation failed: {ratio:.1%} preserved (need 95%+)", file=sys.stderr)
            return False

        orig_galaxies = set(re.findall(r'### GALAXY: ([^\n]+)', original))
        reorg_galaxies = set(re.findall(r'### GALAXY: ([^\n]+)', reorganized))
        if orig_galaxies - reorg_galaxies:
            print(f"Missing galaxies: {orig_galaxies - reorg_galaxies}", file=sys.stderr)
            return False

        orig_facts = len(re.findall(r'\[FACT\]:', original))
        reorg_facts = len(re.findall(r'\[FACT\]:', reorganized))
        if reorg_facts < orig_facts * 0.95:
            print(f"Facts lost: {orig_facts} -> {reorg_facts}", file=sys.stderr)
            return False

        print(f"Validation passed: {ratio:.1%} preserved, {len(reorg_galaxies)} galaxies, {reorg_facts} facts")
        return True

    def fix(self) -> bool:
        if not WORLD_KNOWLEDGE_PATH.exists():
            print("world_knowledge.md not found", file=sys.stderr)
            return False

        content = WORLD_KNOWLEDGE_PATH.read_text()

        # Backup
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = WORLD_KNOWLEDGE_PATH.parent / f"world_knowledge.{timestamp}.backup"
        backup.write_text(content)
        print(f"Backup: {backup.name}")

        print(f"Sending to Kimi K2 ({len(content)} chars)...")

        prompt = f"""Reorganize this knowledge base:

---
{content}
---

Use Cluster > Galaxy > Sun > Fact hierarchy.
Preserve ALL [FACT]: blocks and timestamps.
Return ONLY the reorganized markdown."""

        fixed = self.call_kimi(prompt)

        if not fixed or len(fixed) < len(content) * 0.5:
            print("Kimi response invalid", file=sys.stderr)
            return False

        if not self.validate(content, fixed):
            return False

        WORLD_KNOWLEDGE_PATH.write_text(fixed)
        print("Saved reorganized world_knowledge.md")
        return True

# --- Investigation Mode ---
async def investigate(topic: str, append: bool = True, run_librarian: bool = False):
    """Run full investigation on a topic."""
    print(f"\nW08 Investigation: {topic}")
    print("=" * 50)
    print(f"Model: {RESEARCH_MODEL}")
    print(f"KB: {WORLD_KNOWLEDGE_PATH}")
    print("=" * 50)

    state.seed = topic
    state.context = build_system_prompt(topic)
    state.chat_history = []
    state.previous_searches = []
    state.cycle_count = 0

    # Run 3 reasoning cycles
    for cycle in range(3):
        print(f"\n--- Cycle {cycle + 1}/3 ---")
        answer, searches = reasoning_cycle(state.seed)
        state.cycle_count += 1

        if not answer:
            print("No response received, stopping.")
            break

        if state.cycle_count >= 3 or not searches:
            print("\nMeta-reflection...")
            result = meta_reflect()
            if result == "conclude":
                print("Research concluded.")
                break
            elif result == "need_more" and searches:
                state.seed = searches[0]
                continue
            else:
                break

        if searches:
            print(f"Next search: {searches[0]}")
            state.seed = searches[0]

    # Export
    print("\n--- Exporting results ---")

    if append:
        summary = generate_final_summary(topic)
        if not summary:
            print("Summary generation failed, falling back to raw context", file=sys.stderr)
            summary = state.context

        append_to_world_knowledge(topic, summary)

        if run_librarian:
            print("\nReorganizing KB with Kimi K2...")
            librarian = Librarian()
            librarian.fix()

    print(f"\nInvestigation complete: {topic}")

# --- Main Entry ---
def main():
    if len(sys.argv) < 2:
        print("W08 World Knowledge Worker")
        print("=" * 40)
        print(f"Research model: {RESEARCH_MODEL}")
        print(f"Librarian model: {LIBRARIAN_MODEL}")
        print(f"KB path: {WORLD_KNOWLEDGE_PATH}")
        print()
        print("Usage:")
        print("  python3 W08_world_knowledge.py investigate \"topic\"")
        print("  python3 W08_world_knowledge.py fix")
        print("  python3 W08_world_knowledge.py batch \"t1\" \"t2\" ...")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "investigate":
        if len(sys.argv) < 3:
            print("Usage: investigate \"topic\" [--librarian]")
            sys.exit(1)

        run_librarian = False
        topic_parts = []
        for arg in sys.argv[2:]:
            if arg == "--librarian":
                run_librarian = True
            else:
                topic_parts.append(arg)

        topic = " ".join(topic_parts)
        asyncio.run(investigate(topic, run_librarian=run_librarian))

    elif cmd == "fix":
        librarian = Librarian()
        if not librarian.fix():
            # Restore from backup
            backups = sorted(WORLD_KNOWLEDGE_PATH.parent.glob("world_knowledge.*.backup"), reverse=True)
            if backups:
                WORLD_KNOWLEDGE_PATH.write_text(backups[0].read_text())
                print(f"Restored from: {backups[0].name}")
            sys.exit(1)

    elif cmd == "batch":
        if len(sys.argv) < 3:
            print("Usage: batch \"topic1\" \"topic2\" ...")
            sys.exit(1)
        topics = []
        run_librarian = False
        for arg in sys.argv[2:]:
            if arg == "--librarian":
                run_librarian = True
            else:
                topics.append(arg)

        print(f"Batch mode: {len(topics)} topics")
        for i, topic in enumerate(topics, 1):
            print(f"\n[{i}/{len(topics)}] {topic}")
            asyncio.run(investigate(topic, run_librarian=run_librarian))
        print(f"\nBatch complete: {len(topics)} topics")

    elif cmd == "daily-report":
        recipient = "recipient@example.com"
        limit = 5
        for i, arg in enumerate(sys.argv):
            if arg == "--to" and i + 1 < len(sys.argv):
                recipient = sys.argv[i + 1]
            if arg == "--limit" and i + 1 < len(sys.argv):
                limit = int(sys.argv[i + 1])

        email_daily_report(recipient, limit=limit)

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
