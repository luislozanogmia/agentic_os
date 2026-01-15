# .claude/skills/ax_executor/text_cleaning.py
"""
Comprehensive text cleaning utilities for automation, OCR, and user input processing.
Handles quote removal, formatting normalization, OCR artifacts, and text sanitization.
"""

import re
import unicodedata
from typing import Dict, Optional

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

def fix_simple_typos(text: str) -> str:
    """Fix simple typos using TextBlob if available"""
    if not TEXTBLOB_AVAILABLE:
        return text
    try:
        return str(TextBlob(text).correct())
    except:
        return text

def clean_automation_text(raw: str, placeholders: Optional[Dict[str, str]] = None) -> str:
    """
    Clean text for automation use - removes formatting, quotes, and replaces placeholders.
    
    Args:
        raw: Raw text input
        placeholders: Optional dict of {placeholder: replacement} values
    
    Returns:
        Cleaned text ready for automation
    """
    if not raw:
        return ""
    
    # Extract content from various formatting
    cleaned = extract_content_from_formatting(raw.strip())
    
    # Replace placeholders if provided
    if placeholders:
        for placeholder, replacement in placeholders.items():
            # Handle both {PLACEHOLDER} and PLACEHOLDER formats
            cleaned = cleaned.replace(f"{{{placeholder}}}", replacement)
            cleaned = cleaned.replace(placeholder, replacement)
    
    return cleaned.strip()

def clean_ocr_text(text: str) -> str:
    """Clean OCR output - remove artifacts, fix spacing, normalize characters"""
    if not text:
        return ""
    
    # Remove common OCR artifacts
    text = remove_ocr_artifacts(text)
    
    # Fix spacing issues
    text = fix_spacing(text)
    
    # Normalize characters
    text = normalize_text(text)
    
    return text.strip()

def remove_ocr_artifacts(text: str) -> str:
    """Remove common OCR scanning artifacts"""
    # Remove coordinate-like patterns (e.g., "123,456" at start of lines)
    text = re.sub(r'^\d+,\d+\s*', '', text, flags=re.MULTILINE)
    
    # Remove standalone numbers/coordinates
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
    
    # Remove scanning noise patterns
    text = re.sub(r'[|]{2,}', '', text)  # Multiple pipes
    text = re.sub(r'[_]{3,}', '', text)  # Multiple underscores
    text = re.sub(r'[.]{4,}', '', text)  # Multiple dots
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text

def fix_spacing(text: str) -> str:
    """Fix common spacing issues in text"""
    # Fix missing spaces after punctuation
    text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
    
    # Fix extra spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Fix spaces around punctuation
    text = re.sub(r'\s+([,.!?;:])', r'\1', text)
    text = re.sub(r'([.!?:])\s*([A-Z])', r'\1 \2', text)
    
    return text

def extract_content_from_formatting(text: str) -> str:
    """Extract actual content from various text formatting (quotes, code blocks, etc.)"""
    text = text.strip()
    
    # Handle various formatting patterns
    case_type = detect_formatting_type(text)
    
    if case_type == "wrapped_code_block":
        text = remove_outer_quotes(text)
        return normalize_text_case(remove_code_block(text))
    
    elif case_type == "markdown_with_language":
        return normalize_text_case(remove_code_block(text))
    
    elif case_type == "quoted_with_explanation":
        text = extract_first_part(text)
        return normalize_text_case(remove_outer_quotes(text))
    
    elif case_type == "labeled_content":
        return extract_labeled_content(text)
    
    elif case_type == "simple_quote":
        return normalize_text_case(remove_outer_quotes(text))
    
    # Progressive cleaning for complex cases
    prev = None
    iterations = 0
    while text != prev and iterations < 5:  # Prevent infinite loops
        prev = text
        text = remove_outer_quotes(text)
        text = remove_code_block(text)
        text = remove_formatting_artifacts(text)
        text = extract_first_part(text)
        iterations += 1
    
    return normalize_text_case(text)

def detect_formatting_type(text: str) -> str:
    """Detect the type of text formatting"""
    text = text.strip()
    
    if re.match(r'^"```(json|plaintext|python)?\n(.|\n)+\n```"$', text):
        return "wrapped_code_block"
    elif text.startswith("```") and text.endswith("```"):
        return "markdown_with_language"
    elif text.startswith('"') and "\n\n" in text:
        return "quoted_with_explanation"
    elif re.match(r'^(\*\*[^:]+\*\*|[A-Z_]+):\s*".*"$', text):
        return "labeled_content"
    elif text.startswith('"') and text.endswith('"'):
        return "simple_quote"
    
    return "plain_text"

def remove_outer_quotes(text: str) -> str:
    """Remove outer quotes (single, double, or triple)"""
    text = text.strip()
    
    # Triple quotes
    if (text.startswith('"""') and text.endswith('"""')) or \
       (text.startswith("'''") and text.endswith("'''")):
        return text[3:-3].strip()
    
    # Single/double quotes
    if (text.startswith('"') and text.endswith('"')) or \
       (text.startswith("'") and text.endswith("'")):
        return text[1:-1].strip()
    
    return text

def remove_code_block(text: str) -> str:
    """Remove markdown code block formatting"""
    text = text.strip()
    
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            # Remove first and last lines (```language and ```)
            content = "\n".join(lines[1:-1]).strip()
            # Remove language specifier if it's the only thing on first line
            content = re.sub(r'^(json|python|plaintext|text)\n', '', content, flags=re.IGNORECASE)
            # Handle escaped characters
            try:
                content = content.encode().decode('unicode_escape')
            except:
                pass  # If decode fails, keep original
            return content.strip()
        
        # Simple case - just remove the backticks
        return text.replace("```plaintext", "").replace("```json", "").replace("```python", "").replace("```", "").strip()
    
    return text

def remove_formatting_artifacts(text: str) -> str:
    """Remove common formatting artifacts from text"""
    lines = text.strip().splitlines()
    cleaned = []
    
    for line in lines:
        # Remove common prefixes/artifacts
        cleaned_line = re.sub(
            r'^(---.*?---\s*|\s*(#|>>>|\*{1,2}[^:]+:{0,1}|\*|-+|>+|`{3,}|"{3}|\'{3}|[A-Z_]+:))\s*',
            '',
            line
        )
        
        if cleaned_line.strip():
            cleaned.append(cleaned_line)
    
    return "\n".join(cleaned).strip()

def extract_first_part(text: str) -> str:
    """Extract the first meaningful part before explanations"""
    return text.split("\n\n")[0].strip() if "\n\n" in text else text

def extract_labeled_content(text: str) -> str:
    """Extract content from labeled text (e.g., 'Subject: "content"')"""
    # Match patterns like **Label**: "content" or LABEL: "content"
    match = re.match(r'^\*\*(.+)\*\*:\s*"(.*)"$', text)
    if match:
        return match.group(2).strip()
    
    match = re.match(r'^([A-Z_]+):\s*"(.*)"$', text)
    if match:
        return match.group(2).strip()
    
    return text

def normalize_text_case(text: str) -> str:
    """Intelligently normalize text case - avoid over-capitalizing UI elements"""
    if not text:
        return text
    
    text = text.strip()
    
    # Skip normalization for multiline content
    if "\n" in text:
        return text
    
    words = text.split()
    
    # If it looks like UI text (short, mostly caps, no punctuation), make it lowercase
    if (len(words) <= 7 and
        sum(w[0].isupper() for w in words if w and w[0].isalpha()) >= len(words) - 1 and
        not any(p in text for p in '.!?{}[]:()')):
        return text[0].lower() + text[1:] if text else text
    
    return text

def normalize_text(text: str) -> str:
    """Normalize unicode characters and basic formatting"""
    if not text:
        return ""
    
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    
    # Remove control characters but keep printable ones
    text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char in '\n\t')
    
    return text.strip()

def remove_leading_label(text: str, label: str) -> str:
    """Remove leading labels like 'Subject:' or 'Body:' from text"""
    if not text or not label:
        return text
    
    pattern = rf'^\s*{re.escape(label)}:\s*'
    return re.sub(pattern, '', text, count=1, flags=re.IGNORECASE).strip()

def sanitize_user_input(text: str) -> str:
    """Sanitize user input for safe processing"""
    if not text:
        return ""
    
    # Clean basic formatting
    text = clean_automation_text(text)
    
    # Remove potentially dangerous patterns
    text = re.sub(r'[<>{}]', '', text)  # Remove brackets that could be injection
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def prepare_text_for_automation(text: str, context: Optional[Dict[str, str]] = None) -> str:
    """Prepare text for automation - comprehensive cleaning pipeline"""
    if not text:
        return ""
    
    # Step 1: Extract from formatting
    cleaned = extract_content_from_formatting(text)
    
    # Step 2: OCR artifact removal if it looks like OCR output
    if re.search(r'\d+,\d+|\|{2,}|_{3,}', cleaned):
        cleaned = clean_ocr_text(cleaned)
    
    # Step 3: Replace context placeholders
    if context:
        cleaned = clean_automation_text(cleaned, context)
    
    # Step 4: Final normalization
    cleaned = normalize_text(cleaned)
    
    return cleaned.strip()