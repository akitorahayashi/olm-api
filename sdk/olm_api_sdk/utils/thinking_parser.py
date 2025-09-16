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
        Handles tags that are split across chunks.
        """
        if not chunk:
            return

        self.partial_tag_buffer += chunk

        while True:
            if self.in_think_tag:
                # We are inside a <think> block, looking for </think>
                end_tag_pos = self.partial_tag_buffer.find("</think>")
                if end_tag_pos != -1:
                    # Found the end tag. Yield thinking content.
                    thinking_content = self.partial_tag_buffer[:end_tag_pos]
                    if thinking_content:
                        yield {
                            "type": ContentType.THINKING.value,
                            "content": thinking_content,
                        }
                    # Move buffer past the tag and change state
                    self.partial_tag_buffer = self.partial_tag_buffer[
                        end_tag_pos + len("</think>") :
                    ]
                    self.in_think_tag = False
                else:
                    # End tag not found. The buffer might end with a partial tag.
                    # Yield everything except the partial tag.
                    send_up_to = len(self.partial_tag_buffer)
                    for i in range(len(self.partial_tag_buffer)):
                        if "</think>".startswith(self.partial_tag_buffer[i:]):
                            send_up_to = i
                            break

                    content_to_yield = self.partial_tag_buffer[:send_up_to]
                    if content_to_yield:
                        yield {
                            "type": ContentType.THINKING.value,
                            "content": content_to_yield,
                        }
                    self.partial_tag_buffer = self.partial_tag_buffer[send_up_to:]
                    break  # Wait for more chunks
            else:
                # We are outside a <think> block, looking for <think>
                start_tag_pos = self.partial_tag_buffer.find("<think>")
                if start_tag_pos != -1:
                    # Found the start tag. Yield content before it.
                    content = self.partial_tag_buffer[:start_tag_pos]
                    if content:
                        yield {"type": ContentType.CONTENT.value, "content": content}
                    # Move buffer past the tag and change state
                    self.partial_tag_buffer = self.partial_tag_buffer[
                        start_tag_pos + len("<think>") :
                    ]
                    self.in_think_tag = True
                else:
                    # Start tag not found. The buffer might end with a partial tag.
                    # Yield everything except the partial tag.
                    send_up_to = len(self.partial_tag_buffer)
                    for i in range(len(self.partial_tag_buffer)):
                        if "<think>".startswith(self.partial_tag_buffer[i:]):
                            send_up_to = i
                            break

                    content_to_yield = self.partial_tag_buffer[:send_up_to]
                    if content_to_yield:
                        yield {
                            "type": ContentType.CONTENT.value,
                            "content": content_to_yield,
                        }
                    self.partial_tag_buffer = self.partial_tag_buffer[send_up_to:]
                    break  # Wait for more chunks


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
        "full_response": raw_content,  # Original complete response
    }
