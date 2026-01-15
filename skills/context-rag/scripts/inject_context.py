#!/usr/bin/env python3
"""
Context Injection Helper

Formats search results for natural integration into responses.
Handles deduplication, ordering, and markdown formatting.

Usage:
    python inject_context.py --results results.json --format markdown
    python inject_context.py --results results.json --format plain
"""

import json
import sys
from typing import List, Dict


def deduplicate_results(results: List[Dict]) -> List[Dict]:
    """
    Remove duplicate or near-duplicate results.

    Returns deduplicated list, prioritizing higher scores.
    """
    seen_titles = set()
    deduplicated = []

    for result in results:
        title = result.get('title', '').strip()

        # Exact match
        if title in seen_titles:
            continue

        # Similar title (case-insensitive substring)
        similar = False
        for seen in seen_titles:
            if title.lower() in seen.lower() or seen.lower() in title.lower():
                similar = True
                break

        if not similar:
            deduplicated.append(result)
            seen_titles.add(title)

    return deduplicated


def format_markdown(results: List[Dict]) -> str:
    """Format results as markdown for injection."""
    if not results:
        return ""

    output = []
    output.append("## Relevant Context from Knowledge Bases\n")

    for i, result in enumerate(results, 1):
        score_percent = int(result.get('score', 0) * 100)
        title = result.get('title', 'Unknown')
        source = result.get('file', 'Unknown').replace('.md', '')

        output.append(f"### {i}. {title}")
        output.append(f"*From {source} (relevance: {score_percent}%)*\n")

        # Content
        content = result.get('content', '')
        output.append(content)
        output.append("")

    return "\n".join(output)


def format_plain(results: List[Dict]) -> str:
    """Format results as plain text for integration."""
    if not results:
        return ""

    output = []

    for result in results:
        score_percent = int(result.get('score', 0) * 100)
        title = result.get('title', 'Unknown')

        output.append(f"• {title} ({score_percent}%)")

    return "\n".join(output)


def format_compact(results: List[Dict]) -> str:
    """Format results very compact for inline injection."""
    if not results:
        return ""

    output = []

    for result in results:
        title = result.get('title', 'Unknown')
        # Just the title, ultra-minimal
        output.append(f"- {title}")

    return "\n".join(output)


def integrate_with_response(context: str, response: str, position: str = "end") -> str:
    """
    Integrate formatted context into existing response.

    Args:
        context: Formatted context to inject
        response: Original response text
        position: "end", "start", or "after_intro"

    Returns: Modified response with context injected
    """
    if not context:
        return response

    if position == "end":
        return f"{response}\n\n{context}"

    elif position == "start":
        return f"{context}\n\n{response}"

    elif position == "after_intro":
        # Find first paragraph break and insert after it
        parts = response.split('\n\n', 1)
        if len(parts) > 1:
            return f"{parts[0]}\n\n{context}\n\n{parts[1]}"
        else:
            return f"{context}\n\n{response}"

    return response


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Format and inject context')
    parser.add_argument('--results', required=True, help='JSON file with search results')
    parser.add_argument('--format', choices=['markdown', 'plain', 'compact'], default='markdown',
                       help='Output format')
    parser.add_argument('--deduplicate', action='store_true', default=True,
                       help='Remove duplicate results')
    parser.add_argument('--max-results', type=int, default=4,
                       help='Max results to include')

    args = parser.parse_args()

    # Load results
    try:
        with open(args.results, 'r') as f:
            results = json.load(f)
    except Exception as e:
        print(f"❌ Could not load results: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(results, list):
        results = [results]

    # Process
    if args.deduplicate:
        results = deduplicate_results(results)

    results = results[:args.max_results]

    # Format
    if args.format == 'markdown':
        output = format_markdown(results)
    elif args.format == 'plain':
        output = format_plain(results)
    else:  # compact
        output = format_compact(results)

    print(output)


if __name__ == '__main__':
    main()
