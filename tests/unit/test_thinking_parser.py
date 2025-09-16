"""Tests for thinking parser utilities."""

from sdk.olm_api_sdk.utils.thinking_parser import (
    ThinkingParser,
    create_enhanced_response,
    parse_thinking_response,
)


class TestThinkingParser:
    """Test ThinkingParser class."""

    def test_parse_simple_thinking_response(self):
        """Test parsing a simple response with thinking."""
        text = "<think>Let me calculate 2+2. That's 4.</think>The answer is 4."

        parser = ThinkingParser()
        result = parser.parse_complete_response(text)

        assert result["thinking"] == "Let me calculate 2+2. That's 4."
        assert result["content"] == "The answer is 4."
        assert result["raw"] == text

    def test_parse_no_thinking_tags(self):
        """Test parsing response without thinking tags."""
        text = "The answer is 4."

        parser = ThinkingParser()
        result = parser.parse_complete_response(text)

        assert result["thinking"] == ""
        assert result["content"] == "The answer is 4."
        assert result["raw"] == text

    def test_parse_multiple_thinking_blocks(self):
        """Test parsing response with multiple thinking blocks."""
        text = "<think>First thought</think>Some content<think>Second thought</think>More content"

        parser = ThinkingParser()
        result = parser.parse_complete_response(text)

        assert result["thinking"] == "First thought\nSecond thought"
        assert result["content"] == "Some contentMore content"
        assert result["raw"] == text

    def test_parse_empty_response(self):
        """Test parsing empty response."""
        parser = ThinkingParser()
        result = parser.parse_complete_response("")

        assert result["thinking"] == ""
        assert result["content"] == ""
        assert result["raw"] == ""

    def test_streaming_chunk_parsing_simple(self):
        """Test streaming parsing with simple thinking."""
        parser = ThinkingParser()

        chunks = ["<think>", "Calculating", "</think>", "Result: 4"]
        results = []

        for chunk in chunks:
            results.extend(list(parser.parse_streaming_chunk(chunk)))

        # Should yield thinking content then regular content
        assert len(results) == 2
        assert results[0]["type"] == "thinking"
        assert results[0]["content"] == "Calculating"
        assert results[1]["type"] == "content"
        assert results[1]["content"] == "Result: 4"

    def test_streaming_chunk_parsing_mixed(self):
        """Test streaming with mixed content and thinking."""
        parser = ThinkingParser()

        chunks = [
            "Initial content ",
            "<think>",
            "thinking here",
            "</think>",
            " final content",
        ]
        results = []

        for chunk in chunks:
            results.extend(list(parser.parse_streaming_chunk(chunk)))

        # Should yield: content, thinking, content
        assert len(results) == 3
        assert results[0]["type"] == "content"
        assert results[0]["content"] == "Initial content "
        assert results[1]["type"] == "thinking"
        assert results[1]["content"] == "thinking here"
        assert results[2]["type"] == "content"
        assert results[2]["content"] == " final content"

    def test_streaming_partial_tags(self):
        """Test streaming with partial tags split across chunks."""
        parser = ThinkingParser()

        # Simulate partial tags
        chunks = [
            "Some content",
            "<thi",
            "nk>Thinking starts",
            " and continues</th",
            "ink>",
            "Final content",
        ]

        results = []
        for chunk in chunks:
            results.extend(list(parser.parse_streaming_chunk(chunk)))

        # Combine adjacent results of the same type for assertion
        combined_results = []
        if results:
            # Filter out empty content
            results = [r for r in results if r["content"]]
            if results:
                combined_results.append(results[0])
                for i in range(1, len(results)):
                    if results[i]["type"] == combined_results[-1]["type"]:
                        combined_results[-1]["content"] += results[i]["content"]
                    else:
                        combined_results.append(results[i])

        assert len(combined_results) == 3

        assert combined_results[0]["type"] == "content"
        assert combined_results[0]["content"] == "Some content"

        assert combined_results[1]["type"] == "thinking"
        assert combined_results[1]["content"] == "Thinking starts and continues"

        assert combined_results[2]["type"] == "content"
        assert combined_results[2]["content"] == "Final content"


class TestUtilityFunctions:
    """Test utility functions."""

    def test_parse_thinking_response(self):
        """Test convenience parsing function."""
        text = "<think>Reasoning here</think>Final answer"
        result = parse_thinking_response(text)

        assert result["thinking"] == "Reasoning here"
        assert result["content"] == "Final answer"

    def test_create_enhanced_response(self):
        """Test enhanced response creation."""
        raw_content = "<think>Let me think</think>The answer is 42"
        result = create_enhanced_response(raw_content)

        assert result["think"] == "Let me think"
        assert result["content"] == "The answer is 42"
        assert result["response"] == raw_content  # Original complete response

    def test_enhanced_response_no_thinking(self):
        """Test enhanced response without thinking tags."""
        raw_content = "Direct answer without thinking"
        result = create_enhanced_response(raw_content)

        assert result["think"] == ""
        assert result["content"] == "Direct answer without thinking"
        assert result["response"] == raw_content
