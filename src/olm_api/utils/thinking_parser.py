"""
Local copy of thinking parser utilities for the API service.
This avoids dependency issues with the SDK during runtime.
"""

import re
from typing import Dict


def parse_thinking_response(text: str) -> Dict[str, str]:
    """
    Parse a complete response into thinking and content parts.

    Args:
        text: Complete response text with potential thinking tags

    Returns:
        Dict with 'thinking', 'content', and 'raw' keys
    """
    if not text:
        return {"thinking": "", "content": "", "raw": text}

    # Extract thinking content using regex
    thinking_pattern = r"<think>(.*?)</think>"
    thinking_matches = re.findall(thinking_pattern, text, re.DOTALL)
    thinking_content = "\n".join(thinking_matches).strip()

    # Remove thinking tags to get actual content
    content_without_thinking = re.sub(
        thinking_pattern, "", text, flags=re.DOTALL
    ).strip()

    return {
        "thinking": thinking_content,
        "content": content_without_thinking,
        "raw": text,
    }
