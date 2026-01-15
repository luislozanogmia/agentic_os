#!/usr/bin/env python3
"""
Context Validation Script

Validates extracted context before injection into responses.
Checks for relevance, completeness, structure, and safety.

Usage:
    python validate_context.py extracted_context.txt
    python validate_context.py --json extracted_context.txt
"""

import os
import sys
import json
import re
from typing import Dict, Tuple


# Validation thresholds
MIN_RELEVANCE_SCORE = 0.6
MIN_SECTION_LENGTH = 50  # Characters
MAX_SECTIONS = 8  # Per query
FORBIDDEN_PATTERNS = [
    r'api[_-]?key',
    r'password',
    r'secret',
    r'token.*=',
    r'auth.*bearer',
]


def validate_markdown_structure(content: str) -> Tuple[bool, str]:
    """
    Validate that markdown structure is intact.
    Checks for unclosed headers, code blocks, lists.

    Returns (is_valid, error_message)
    """
    # Count header markers
    lines = content.split('\n')
    open_code_blocks = 0
    open_lists = 0

    for line in lines:
        # Check code blocks
        if '```' in line:
            open_code_blocks += 1

        # Check if properly closed
        if line.strip().startswith('- ') or line.strip().startswith('* '):
            if not line.startswith((' ', '\t')):
                open_lists += 1

    # Validation
    if open_code_blocks % 2 != 0:
        return False, "Unclosed code block (```)"

    # Check for common truncation patterns
    if content.rstrip().endswith('...'):
        # Might be truncated, but not necessarily invalid
        pass

    return True, ""


def validate_no_secrets(content: str) -> Tuple[bool, str]:
    """
    Validate that content doesn't contain sensitive data.

    Returns (is_safe, reason)
    """
    content_lower = content.lower()

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, content_lower):
            return False, f"Contains potential secret (pattern: {pattern})"

    return True, ""


def validate_relevance(content: str, tokens: list) -> Tuple[bool, float]:
    """
    Validate that content is actually relevant to query.
    At least 2 tokens from query should appear in content.

    Returns (is_relevant, confidence_score)
    """
    content_lower = content.lower()
    matches = sum(1 for token in tokens if token.lower() in content_lower)

    if matches == 0:
        return False, 0.0

    # Confidence = proportion of tokens that matched
    confidence = matches / max(1, len(tokens))

    return confidence >= 0.5, confidence


def validate_completeness(content: str) -> Tuple[bool, str]:
    """
    Validate that content appears complete, not truncated mid-thought.

    Returns (is_complete, reason)
    """
    lines = content.split('\n')

    if len(lines) == 0:
        return False, "Content is empty"

    if len(content) < MIN_SECTION_LENGTH:
        return False, f"Content too short ({len(content)} chars, min {MIN_SECTION_LENGTH})"

    # Check last line
    last_line = lines[-1].strip()

    # Should end with punctuation or valid markdown
    if last_line and not any(last_line.endswith(c) for c in ['.', '!', '?', ')', '`', '```']):
        # Might be truncated, but give it some slack for lists/code
        if not last_line.startswith(('-', '*', '#')):
            # Not definitely incomplete, but suspicious
            return True, "Warning: May be truncated"

    return True, ""


def validate_section_count(content: str) -> Tuple[bool, int]:
    """
    Count sections and validate not too many.

    Returns (is_valid, section_count)
    """
    # Count markdown headers as section markers
    section_count = content.count('\n##')

    if section_count > MAX_SECTIONS:
        return False, section_count

    return True, section_count


def validate_content(content: str, query: str = None) -> Dict:
    """
    Perform comprehensive validation of extracted content.

    Returns dict with all validation results and overall score.
    """
    results = {
        'overall_valid': True,
        'relevance_score': 1.0,
        'checks': {}
    }

    # 1. Markdown structure
    is_valid, error = validate_markdown_structure(content)
    results['checks']['markdown_structure'] = {'passed': is_valid, 'message': error}
    if not is_valid:
        results['overall_valid'] = False

    # 2. No secrets
    is_safe, reason = validate_no_secrets(content)
    results['checks']['no_secrets'] = {'passed': is_safe, 'message': reason}
    if not is_safe:
        results['overall_valid'] = False

    # 3. Completeness
    is_complete, reason = validate_completeness(content)
    results['checks']['completeness'] = {'passed': is_complete, 'message': reason}
    if not is_complete and 'truncated' in reason.lower():
        results['relevance_score'] *= 0.8

    # 4. Section count
    is_valid, count = validate_section_count(content)
    results['checks']['section_count'] = {'passed': is_valid, 'message': f"{count} sections"}
    if not is_valid:
        results['overall_valid'] = False
        results['relevance_score'] *= 0.7

    # 5. Relevance (if query provided)
    if query:
        tokens = [t for t in query.split() if len(t) > 2]
        is_relevant, confidence = validate_relevance(content, tokens)
        results['checks']['relevance'] = {
            'passed': is_relevant,
            'message': f"Confidence: {confidence:.1%}",
            'confidence': confidence
        }
        results['relevance_score'] = confidence

        if not is_relevant:
            results['overall_valid'] = False

    # Overall score
    scores = [
        1.0 if results['checks']['markdown_structure']['passed'] else 0.5,
        1.0 if results['checks']['no_secrets']['passed'] else 0.0,
        0.9 if results['checks']['completeness']['passed'] else 0.5,
        0.9 if results['checks']['section_count']['passed'] else 0.5,
        results['relevance_score'] if 'relevance' in results['checks'] else 0.8,
    ]

    results['validation_score'] = sum(scores) / len(scores)

    return results


def format_validation_report(content: str, validation: Dict, verbose: bool = True) -> str:
    """Format validation report for human reading."""
    report = []

    overall = "✅ VALID" if validation['overall_valid'] else "❌ INVALID"
    score = int(validation['validation_score'] * 100)
    report.append(f"\n{overall} | Validation Score: {score}%\n")

    for check_name, result in validation['checks'].items():
        status = "✓" if result['passed'] else "✗"
        report.append(f"{status} {check_name.replace('_', ' ').title()}: {result.get('message', '')}")

    if verbose:
        report.append(f"\nContent preview ({len(content)} chars):")
        preview = content[:200] + "..." if len(content) > 200 else content
        report.append(f"  {preview}")

    return "\n".join(report)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Validate extracted context')
    parser.add_argument('file', nargs='?', help='File to validate (or stdin if not provided)')
    parser.add_argument('--query', help='Original query for relevance check')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--verbose', action='store_true', default=True, help='Verbose output')

    args = parser.parse_args()

    # Read content
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Could not read file: {e}")
            sys.exit(1)
    else:
        content = sys.stdin.read()

    if not content:
        print("❌ No content to validate")
        sys.exit(1)

    # Validate
    validation = validate_content(content, args.query)

    # Output
    if args.json:
        print(json.dumps(validation, indent=2))
    else:
        print(format_validation_report(content, validation, args.verbose))

    # Exit code: 0 if valid, 1 if invalid
    sys.exit(0 if validation['overall_valid'] else 1)


if __name__ == '__main__':
    main()
