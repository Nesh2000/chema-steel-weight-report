"""
Utility module for Steel Weight Calculator.
Contains common helper functions, constants, and matching logic.
"""

import logging
import re
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


# --- Common Aliases for Stubbing/Matching ---
TMT_BAR_PATTERNS = [
    r"Y(\d+)",
    r"D(\d+)",
    r"(\d+)MM\s*TMT",
    r"TMT\s*(\d+)MM",
    r"(\d+)MM\s*BAR",
    r"(\d+)MM\s*REBAR",
]


def normalize_text(text: str) -> str:
    """
    Normalize text by removing extra whitespace, 
    converting to uppercase, and removing special characters.
    """
    if not text:
        return ""
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    # Convert to uppercase
    text = text.upper()
    # Remove common punctuation that might interfere with matching
    text = text.replace('-', ' ').replace('_', ' ')
    return text.strip()


def extract_diameter_from_alias(alias: str) -> Optional[float]:
    """
    Attempt to extract a diameter value from a product alias/description.
    e.g., 'Y12', 'D12', '12MM' should all return 12.0
    """
    normalized = normalize_text(alias)
    
    # Check for Y or D followed by numbers (e.g., Y12, D12)
    match = re.search(r'[YD](\d+)', normalized)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    
    # Check for number followed by MM or nothing
    match = re.search(r'(\d+)\s*MM', normalized)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    
    # Check for standalone number in the text
    match = re.search(r'\b(\d+)\b', normalized)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    
    return None
