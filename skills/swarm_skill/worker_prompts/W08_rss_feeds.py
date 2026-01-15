#!/usr/bin/env python3
"""
W08 RSS Feed Fetcher - AI News Sources
Feeds W08's curiosity with latest AI news on: small/large models, inference, memory, training

Usage:
    python3 W08_rss_feeds.py fetch          # Get latest topics from all feeds
    python3 W08_rss_feeds.py fetch --limit 5  # Limit topics per feed
    python3 W08_rss_feeds.py run             # Fetch + run W08 investigate on each
"""

import os
import sys
import re
import json
import hashlib
import datetime
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

# --- Configuration ---
HOME = Path.home()
CACHE_FILE = HOME / ".claude" / "skills" / "swarm_skill" / "worker_prompts" / ".rss_cache.json"
W08_SCRIPT = HOME / ".claude" / "skills" / "swarm_skill" / "worker_prompts" / "W08_world_knowledge.py"

# AI-focused RSS feeds
RSS_FEEDS = {
    # Research & Papers (most reliable)
    "arxiv_cs_ai": "https://rss.arxiv.org/rss/cs.AI",
    "arxiv_cs_lg": "https://rss.arxiv.org/rss/cs.LG",  # Machine Learning
    "arxiv_cs_cl": "https://rss.arxiv.org/rss/cs.CL",  # Computation & Language (NLP)

    # News & Blogs
    "huggingface": "https://huggingface.co/blog/feed.xml",
    "deepmind": "https://deepmind.google/blog/rss.xml",
    "nvidia_ai": "https://blogs.nvidia.com/feed/",

    # Community & Aggregators
    "hn_ai": "https://hnrss.org/newest?q=AI+OR+LLM+OR+transformer+OR+inference",
    "hn_ml": "https://hnrss.org/newest?q=machine+learning+OR+neural+network+OR+training",
    "papers_with_code": "https://paperswithcode.com/latest",
}

# Keywords to filter relevant content
KEYWORDS = [
    # Models
    "llm", "language model", "transformer", "attention", "gpt", "llama", "mistral",
    "qwen", "deepseek", "phi", "gemma", "claude", "gemini", "small model", "large model",
    "7b", "8b", "13b", "30b", "70b", "405b", "moe", "mixture of experts",

    # Inference
    "inference", "quantization", "int4", "int8", "gguf", "ggml", "vllm", "tgi",
    "speculative decoding", "kv cache", "context length", "throughput", "latency",
    "mlx", "llama.cpp", "exllama", "awq", "gptq",

    # Memory
    "memory", "context window", "rag", "retrieval", "vector", "embedding",
    "long context", "rope", "alibi", "flash attention", "paged attention",

    # Training
    "training", "fine-tuning", "lora", "qlora", "dpo", "rlhf", "sft",
    "pretraining", "curriculum", "distillation", "pruning", "merging",
    "dataset", "synthetic data", "alignment",
]

def load_cache() -> Dict:
    """Load seen article hashes from cache."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except:
            pass
    return {"seen": [], "last_fetch": None}

def save_cache(cache: Dict):
    """Save cache to disk."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2))

def hash_title(title: str) -> str:
    """Create hash of title for deduplication."""
    return hashlib.md5(title.lower().encode()).hexdigest()[:12]

def fetch_rss(url: str, timeout: int = 15) -> List[Dict]:
    """Fetch and parse RSS feed."""
    try:
        req = Request(url, headers={"User-Agent": "W08-RSS-Fetcher/1.0"})
        with urlopen(req, timeout=timeout) as response:
            content = response.read()

        root = ET.fromstring(content)
        items = []

        # Handle both RSS and Atom formats
        for item in root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry"):
            title = None
            description = None
            link = None
            published_year = None

            # RSS format
            title_el = item.find("title")
            if title_el is not None:
                title = title_el.text

            desc_el = item.find("description")
            if desc_el is not None:
                description = desc_el.text or ""

            link_el = item.find("link")
            if link_el is not None:
                link = link_el.text

            # Atom format fallback
            if title is None:
                title_el = item.find("{http://www.w3.org/2005/Atom}title")
                if title_el is not None:
                    title = title_el.text

            if description is None:
                summary_el = item.find("{http://www.w3.org/2005/Atom}summary")
                if summary_el is not None:
                    description = summary_el.text or ""

            if link is None:
                link_el = item.find("{http://www.w3.org/2005/Atom}link")
                if link_el is not None:
                    link = link_el.get("href")

            if not published_year:
                date_el = item.find("pubDate")
                if date_el is not None and date_el.text:
                    try:
                        published_year = parsedate_to_datetime(date_el.text).year
                    except Exception:
                        published_year = None

            if not published_year:
                updated_el = item.find("updated") or item.find("{http://www.w3.org/2005/Atom}updated")
                if updated_el is not None and updated_el.text:
                    try:
                        published_year = parsedate_to_datetime(updated_el.text).year
                    except Exception:
                        published_year = None

            if title:
                items.append({
                    "title": title.strip(),
                    "description": (description or "").strip()[:500],
                    "link": link,
                    "year": published_year
                })

        return items
    except Exception as e:
        print(f"  Error fetching {url}: {e}", file=sys.stderr)
        return []

def is_relevant(title: str, description: str) -> bool:
    """Check if article matches AI keywords."""
    text = (title + " " + description).lower()
    return any(kw in text for kw in KEYWORDS)

def extract_research_topic(title: str, description: str) -> str:
    """Convert article title to research topic."""
    # Clean up common prefixes
    topic = title
    topic = re.sub(r'^\[.*?\]\s*', '', topic)  # Remove [arXiv:...] etc
    topic = re.sub(r'^(Paper:|Article:|Blog:)\s*', '', topic, flags=re.I)

    # Truncate if too long
    if len(topic) > 100:
        topic = topic[:100] + "..."

    return topic.strip()

def fetch_all_feeds(limit_per_feed: int = 3) -> List[str]:
    """Fetch topics from all RSS feeds."""
    cache = load_cache()
    seen = set(cache.get("seen", []))
    new_topics = []

    print(f"Fetching from {len(RSS_FEEDS)} feeds...")

    for name, url in RSS_FEEDS.items():
        print(f"  {name}...", end=" ", flush=True)
        items = fetch_rss(url)

        count = 0
        for item in items:
            if count >= limit_per_feed:
                break

            # Make sure feed item is from 2026 or newer
            year = item.get("year")
            if year is not None and year < 2026:
                continue

            title = item["title"]
            desc = item.get("description", "")

            # Skip if seen
            h = hash_title(title)
            if h in seen:
                continue

            # Skip if not relevant
            if not is_relevant(title, desc):
                continue

            # Extract topic and add
            topic = extract_research_topic(title, desc)
            if topic:
                new_topics.append(topic)
                seen.add(h)
                count += 1

        print(f"{count} new")

    # Update cache
    cache["seen"] = list(seen)[-1000:]  # Keep last 1000
    cache["last_fetch"] = datetime.datetime.now().isoformat()
    save_cache(cache)

    return new_topics

def run_w08_on_topics(topics: List[str], max_topics: int = 10, librarian: bool = False):
    """Run W08 investigate on each topic."""
    if not W08_SCRIPT.exists():
        print(f"W08 script not found: {W08_SCRIPT}", file=sys.stderr)
        return

    topics = topics[:max_topics]
    print(f"\nRunning W08 on {len(topics)} topics...")

    for i, topic in enumerate(topics, 1):
        print(f"\n[{i}/{len(topics)}] {topic}")
        print("-" * 50)

        try:
            cmd = [
                "python3",
                str(W08_SCRIPT),
                "investigate",
                topic,
            ]
            if librarian:
                cmd.append("--librarian")

            subprocess.run(
                cmd,
                timeout=300  # 5 min per topic
            )
        except subprocess.TimeoutExpired:
            print(f"Timeout on topic: {topic}", file=sys.stderr)
        except KeyboardInterrupt:
            print("\nInterrupted by user")
            break
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

def main():
    if len(sys.argv) < 2:
        print("W08 RSS Feed Fetcher")
        print("=" * 40)
        print(f"Configured feeds: {len(RSS_FEEDS)}")
        print(f"Keywords: {len(KEYWORDS)}")
        print()
        print("Usage:")
        print("  python3 W08_rss_feeds.py fetch           # Get new topics")
        print("  python3 W08_rss_feeds.py fetch --limit 5 # Limit per feed")
        print("  python3 W08_rss_feeds.py run             # Fetch + investigate")
        print("  python3 W08_rss_feeds.py run --max 10    # Limit investigations")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    # Parse args
    limit = 3
    max_topics = 10
    librarian = False
    for i, arg in enumerate(sys.argv):
        if arg == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
        if arg == "--max" and i + 1 < len(sys.argv):
            max_topics = int(sys.argv[i + 1])
        if arg == "--librarian":
            librarian = True

    if cmd == "fetch":
        topics = fetch_all_feeds(limit_per_feed=limit)
        print(f"\nFound {len(topics)} new topics:")
        for t in topics:
            print(f"  - {t}")

    elif cmd == "run":
        topics = fetch_all_feeds(limit_per_feed=limit)
        if topics:
            run_w08_on_topics(topics, max_topics=max_topics, librarian=librarian)
        else:
            print("No new topics to investigate")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
