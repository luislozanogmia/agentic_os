#!/usr/bin/env python3
"""
Context RAG Search Script

Searches world_knowledge.md and ~/Documents/artificial_minds/memory_palace.md for relevant context.
Implements OR-based keyword matching with relevance scoring.

Usage:
    python search_function.py "topic"
    python search_function.py --query "topic"
    python search_function.py "topic" --source world|memory|both
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Tuple, Dict

# Configuration
WORLD_KNOWLEDGE_FILE = os.path.expanduser("~/Documents/artificial_minds/world_knowledge.md")
MEMORY_PALACE_FILE = os.path.expanduser("~/Documents/artificial_minds/memory_palace.md")
MAX_SECTIONS_PER_SOURCE = 4
MIN_RELEVANCE_SCORE = 0.5


def extract_sections(content: str, filename: str) -> List[Dict]:
    """
    Extract markdown sections (delimited by ## headers) from content.

    Returns list of dicts with: title, content, start_line, end_line
    """
    sections = []
    lines = content.split('\n')
    current_section = None
    section_start = 0

    for i, line in enumerate(lines):
        # Detect markdown header (##)
        if line.startswith('## '):
            # Save previous section if exists
            if current_section:
                section_content = '\n'.join(lines[section_start:i]).strip()
                sections.append({
                    'title': current_section,
                    'content': section_content,
                    'start_line': section_start,
                    'end_line': i,
                    'file': filename
                })

            # Start new section
            current_section = line[3:].strip()  # Remove "## "
            section_start = i

    # Don't forget last section
    if current_section:
        section_content = '\n'.join(lines[section_start:]).strip()
        sections.append({
            'title': current_section,
            'content': section_content,
            'start_line': section_start,
            'end_line': len(lines),
            'file': filename
        })

    return sections


def tokenize_query(query: str) -> List[str]:
    """
    Tokenize query into lowercase words.
    Remove common stop words.
    """
    stop_words = {'a', 'an', 'and', 'the', 'or', 'for', 'of', 'to', 'in', 'is', 'was', 'be', 'are'}

    tokens = [
        word.lower().strip('.,!?;:')
        for word in query.split()
        if word.lower().strip('.,!?;:') not in stop_words and len(word) > 2
    ]

    return tokens


def score_section(section: Dict, tokens: List[str]) -> Tuple[float, Dict]:
    """
    Score a section based on token matches.

    Scoring:
    - Base: 1 point per unique token match (max 1.0 from base)
    - Frequency: +0.1 per additional occurrence of any token
    - Title match: +0.3 if token appears in section title

    Returns (score, match_info)
    """
    content = section['content'].lower()
    title = section['title'].lower()

    score = 0.0
    match_info = {
        'matched_tokens': [],
        'match_count': 0,
        'title_match': False
    }

    # Check each token
    unique_matches = set()
    for token in tokens:
        if token in content:
            unique_matches.add(token)
            match_info['matched_tokens'].append(token)

            # Count occurrences
            count = content.count(token)
            match_info['match_count'] += count

            # Title bonus
            if token in title:
                match_info['title_match'] = True

    # Calculate score
    # Base: 0.5 points for each unique match (max 1.0 if all tokens match)
    base_score = min(len(unique_matches) / max(1, len(tokens)) * 0.5, 0.5)

    # Frequency: 0.1 per match (capped)
    frequency_bonus = min(match_info['match_count'] * 0.05, 0.3)

    # Title bonus
    title_bonus = 0.2 if match_info['title_match'] else 0.0

    score = min(base_score + frequency_bonus + title_bonus, 1.0)

    return score, match_info


def search_source(filepath: str, query: str, max_results: int = MAX_SECTIONS_PER_SOURCE) -> List[Dict]:
    """
    Search a single knowledge source file for relevant sections.

    Returns sorted list of matching sections with scores.
    """
    if not os.path.exists(filepath):
        return []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"⚠️  Could not read {filepath}: {e}", file=sys.stderr)
        return []

    # Extract sections
    filename = os.path.basename(filepath)
    sections = extract_sections(content, filename)

    # Tokenize query
    tokens = tokenize_query(query)
    if not tokens:
        return []

    # Score all sections
    scored_sections = []
    for section in sections:
        score, match_info = score_section(section, tokens)

        if score > 0:  # Only include sections with some match
            section['score'] = score
            section['match_info'] = match_info
            scored_sections.append(section)

    # Sort by score, descending
    scored_sections.sort(key=lambda s: s['score'], reverse=True)

    # Return top N
    return scored_sections[:max_results]

def format_result(result: Dict) -> str:
    """Format search result for display."""
    score_percent = int(result['score'] * 100)
    matched = ', '.join(result['match_info']['matched_tokens'][:3])

    output = f"""
### {result['title']} (Score: {score_percent}%)
**Source**: {result['file']}
**Matched tokens**: {matched}

{result['content'][:500]}...""" if len(result['content']) > 500 else f"""
### {result['title']} (Score: {score_percent}%)
**Source**: {result['file']}
**Matched tokens**: {matched}

{result['content']} """
    return output

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Search knowledge bases')
    parser.add_argument('positional_query', nargs='?', help='Search query')
    parser.add_argument('--query', help='Search query (flag)')
    parser.add_argument('--source', choices=['world', 'memory', 'both'], default='both',
                       help='Which source to search')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()
    
    query = args.positional_query or args.query
    if not query:
        parser.error("Query is required (provide as argument or --query)")

    # Search
    results = []

    if args.source in ['world', 'both']:
        results.extend(search_source(WORLD_KNOWLEDGE_FILE, query))

    if args.source in ['memory', 'both']:
        results.extend(search_source(MEMORY_PALACE_FILE, query))

    # Sort all results by score
    results.sort(key=lambda r: r['score'], reverse=True)

    # Trim to max results total
    results = results[:MAX_SECTIONS_PER_SOURCE * 2]

    # Output
    if args.json:
        # For JSON output, remove non-serializable fields
        json_results = []
        for r in results:
            json_results.append({
                'title': r['title'],
                'score': r['score'],
                'file': r['file'],
                'matched_tokens': r['match_info']['matched_tokens'],
                'content': r['content'][:200]  # Truncate for JSON
            })
        print(json.dumps(json_results, indent=2))
    else:
        # Human-readable output
        if not results:
            print(f"❌ No results found for: {query}")
        else:
            print(f"✅ Found {len(results)} results for: {query}\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']} [{result['file']}] - {int(result['score']*100)}%")

            print("\n" + "="*70)
            for result in results:
                print(format_result(result))


if __name__ == '__main__':
    main()
