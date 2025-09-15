"""
Utilities for parsing thinking content from model responses.

Handles separation of thinking tags from actual content in both
streaming and non-streaming scenarios.
"""

import logging
import re
from enum import Enum
from typing import Dict, Generator

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Types of content that can be parsed."""

    THINKING = "thinking"
    CONTENT = "content"
    RAW = "raw"


class ThinkingParser:
    """
    Parser for separating thinking content from actual responses.

    Handles both streaming chunks and complete responses.
    """

    def __init__(self):
        self.thinking_buffer = ""
        self.content_buffer = ""
        self.current_state = ContentType.CONTENT
        self.in_think_tag = False
        self.think_tag_depth = 0
        self.partial_tag_buffer = ""  # Buffer for partial tags

    def reset(self):
        """Reset parser state for new response."""
        self.thinking_buffer = ""
        self.content_buffer = ""
        self.current_state = ContentType.CONTENT
        self.in_think_tag = False
        self.think_tag_depth = 0
        self.partial_tag_buffer = ""

    def parse_complete_response(self, text: str) -> Dict[str, str]:
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

    def parse_streaming_chunk(
        self, chunk: str
    ) -> Generator[Dict[str, str], None, None]:
        """
        Parse a streaming chunk and yield content with types.

        Simple approach: accumulate text and use regex parsing.
        """
        if not chunk:
            return

        # Accumulate all text
        self.partial_tag_buffer += chunk

        # Try to parse complete tags from accumulated text
        current_text = self.partial_tag_buffer

        # Find all complete thinking blocks
        import re

        # Pattern to find complete thinking blocks
        pattern = r"<think>(.*?)</think>"
        matches = list(re.finditer(pattern, current_text, re.DOTALL))

        last_end = 0

        for match in matches:
            start, end = match.span()
            thinking_content = match.group(1)

            # Yield content before thinking block
            if start > last_end:
                content_before = current_text[last_end:start]
                if content_before.strip():
                    yield {"type": ContentType.CONTENT.value, "content": content_before}

            # Yield thinking content
            if thinking_content.strip():
                yield {"type": ContentType.THINKING.value, "content": thinking_content}

            last_end = end

        # Keep remaining text for next chunk
        if matches:
            self.partial_tag_buffer = current_text[last_end:]

        # If no complete thinking blocks, check if we have content to yield
        if not matches and not (
            "<think>" in current_text and "</think>" not in current_text
        ):
            # No partial thinking tags, yield as content
            if current_text.strip():
                yield {"type": ContentType.CONTENT.value, "content": current_text}
            self.partial_tag_buffer = ""


def parse_thinking_response(text: str) -> Dict[str, str]:
    """
    Convenience function to parse a complete thinking response.

    Args:
        text: Response text that may contain thinking tags

    Returns:
        Dict with separated thinking and content
    """
    parser = ThinkingParser()
    return parser.parse_complete_response(text)


def create_enhanced_response(raw_content: str) -> Dict[str, str]:
    """
    Create enhanced response format with separated thinking/content.

    Args:
        raw_content: Raw response from ollama

    Returns:
        Enhanced response with think, content, and response fields
    """
    parsed = parse_thinking_response(raw_content)

    return {
        "think": parsed["thinking"],  # Thinking process
        "content": parsed["content"],  # Clean response without think tags
        "response": raw_content,  # Original complete response
    }
