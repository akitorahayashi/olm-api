import asyncio
import os
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest

from sdk.olm_api_client.v2.mock_client import MockOlmClientV2
from sdk.olm_api_client.v2.protocol import OlmClientV2Protocol


class TestMockOlmClientV2:
    """Comprehensive test suite for MockOlmClientV2"""

    def test_implements_protocol(self):
        """Test that MockOlmClientV2 implements OlmClientV2Protocol"""
        client = MockOlmClientV2()
        assert isinstance(client, OlmClientV2Protocol)

    def test_init_default_values(self):
        """Test initialization with default values"""
        client = MockOlmClientV2()
        assert client.token_delay == 0.01
        assert len(client.mock_responses) == 5  # DEFAULT_RESPONSES length
        assert client.response_index == 0

    def test_init_custom_token_delay(self):
        """Test initialization with custom token delay"""
        custom_delay = 0.05
        client = MockOlmClientV2(token_delay=custom_delay)
        assert client.token_delay == custom_delay

    def test_init_environment_token_delay(self):
        """Test initialization respects MOCK_TOKEN_DELAY environment variable"""
        with patch.dict(os.environ, {"MOCK_TOKEN_DELAY": "0.02"}):
            client = MockOlmClientV2()
            assert client.token_delay == 0.02

    def test_init_explicit_delay_overrides_env(self):
        """Test explicit token_delay overrides environment variable"""
        with patch.dict(os.environ, {"MOCK_TOKEN_DELAY": "0.02"}):
            client = MockOlmClientV2(token_delay=0.03)
            assert client.token_delay == 0.03

    def test_init_custom_responses(self):
        """Test initialization with custom responses"""
        custom_responses = ["Response A", "Response B", "Response C"]
        client = MockOlmClientV2(responses=custom_responses)
        assert client.mock_responses == custom_responses

    def test_init_empty_responses_raises_error(self):
        """Test initialization with empty responses raises ValueError"""
        with pytest.raises(ValueError, match="responses must be a non-empty list"):
            MockOlmClientV2(responses=[])

    def test_init_non_string_responses_raises_error(self):
        """Test initialization with non-string responses raises TypeError"""
        with pytest.raises(TypeError, match="all responses must be str"):
            MockOlmClientV2(responses=["valid", 123, "also valid"])

    @pytest.mark.asyncio
    async def test_generate_non_streaming_format(self):
        """Test non-streaming response follows chat completion format exactly"""
        client = MockOlmClientV2(token_delay=0)
        messages = [{"role": "user", "content": "Hello"}]

        result = await client.generate(messages, "test-model", stream=False)

        # Validate complete chat completion format
        assert isinstance(result, dict)
        assert result["object"] == "chat.completion"
        assert result["model"] == "test-model"
        assert "id" in result
        assert result["id"].startswith("chatcmpl-mock-")
        assert "created" in result
        assert isinstance(result["created"], int)

        # Validate choices structure
        assert "choices" in result
        assert len(result["choices"]) == 1
        choice = result["choices"][0]
        assert choice["index"] == 0
        assert choice["finish_reason"] == "stop"

        # Validate message structure
        assert "message" in choice
        message = choice["message"]
        assert message["role"] == "assistant"
        assert "content" in message
        assert isinstance(message["content"], str)
        assert len(message["content"]) > 0

        # Validate usage structure
        assert "usage" in result
        usage = result["usage"]
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert "total_tokens" in usage
        assert (
            usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
        )

    @pytest.mark.asyncio
    async def test_generate_streaming_format(self):
        """Test streaming response follows streaming chunk format exactly"""
        client = MockOlmClientV2(token_delay=0)
        messages = [{"role": "user", "content": "Hello"}]

        result = await client.generate(messages, "test-model", stream=True)

        # Verify async generator
        assert isinstance(result, AsyncGenerator)

        chunks = []
        async for chunk in result:
            chunks.append(chunk)

        assert len(chunks) >= 3  # role chunk + content chunks + final chunk

        # Validate first chunk (role)
        first_chunk = chunks[0]
        assert first_chunk["object"] == "chat.completion.chunk"
        assert first_chunk["model"] == "test-model"
        assert "id" in first_chunk
        assert first_chunk["choices"][0]["delta"]["role"] == "assistant"
        assert first_chunk["choices"][0]["finish_reason"] is None

        # Validate content chunks (middle chunks)
        content_chunks = chunks[1:-1]
        full_content = ""
        for chunk in content_chunks:
            assert chunk["object"] == "chat.completion.chunk"
            assert chunk["model"] == "test-model"
            assert "content" in chunk["choices"][0]["delta"]
            assert chunk["choices"][0]["finish_reason"] is None
            full_content += chunk["choices"][0]["delta"]["content"]

        assert len(full_content) > 0

        # Validate final chunk
        final_chunk = chunks[-1]
        assert final_chunk["object"] == "chat.completion.chunk"
        assert final_chunk["model"] == "test-model"
        assert final_chunk["choices"][0]["delta"] == {}
        assert final_chunk["choices"][0]["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_generate_with_tools_parameter(self):
        """Test generate method accepts tools parameter (ignored in mock)"""
        client = MockOlmClientV2(token_delay=0)
        messages = [{"role": "user", "content": "Use a tool"}]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_function",
                    "description": "A test function",
                },
            }
        ]

        result = await client.generate(
            messages, "test-model", tools=tools, stream=False
        )

        # Should return normal response (tools ignored in mock)
        assert isinstance(result, dict)
        assert result["object"] == "chat.completion"
        assert result["choices"][0]["message"]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_generate_with_kwargs_parameters(self):
        """Test generate method accepts additional kwargs (ignored in mock)"""
        client = MockOlmClientV2(token_delay=0)
        messages = [{"role": "user", "content": "Hello"}]

        result = await client.generate(
            messages,
            "test-model",
            stream=False,
            temperature=0.7,
            top_p=0.9,
            max_tokens=100,
        )

        # Should return normal response (kwargs ignored in mock)
        assert isinstance(result, dict)
        assert result["object"] == "chat.completion"

    def test_response_cycling(self):
        """Test that responses cycle through the provided list"""
        custom_responses = ["First", "Second", "Third"]
        client = MockOlmClientV2(responses=custom_responses, token_delay=0)
        messages = [{"role": "user", "content": "test"}]

        # Test cycling through responses
        results = []
        for i in range(6):  # More than length of responses
            result = asyncio.run(client.generate(messages, "test-model", stream=False))
            results.append(result["choices"][0]["message"]["content"])

        # Should cycle: First, Second, Third, First, Second, Third
        assert results[0] == "First"
        assert results[1] == "Second"
        assert results[2] == "Third"
        assert results[3] == "First"
        assert results[4] == "Second"
        assert results[5] == "Third"

    def test_tokenize_realistic_basic(self):
        """Test realistic tokenization produces reasonable results"""
        client = MockOlmClientV2()

        # Test simple sentence
        tokens = client._tokenize_realistic("Hello world!")
        assert len(tokens) >= 3  # Should split into multiple tokens
        assert "Hello" in tokens
        assert "world" in tokens
        assert "!" in tokens or "world!" in tokens

    def test_tokenize_realistic_handles_punctuation(self):
        """Test tokenization handles punctuation correctly"""
        client = MockOlmClientV2()

        tokens = client._tokenize_realistic("Hello, world!")
        # Should separate punctuation or keep it attached
        assert len(tokens) > 1
        assert any("Hello" in token for token in tokens)

    def test_tokenize_realistic_handles_long_words(self):
        """Test tokenization may split very long words"""
        client = MockOlmClientV2()

        long_word = "supercalifragilisticexpialidocious"
        tokens = client._tokenize_realistic(long_word)
        # May split long words (20% chance), but should at least return the word
        assert len(tokens) >= 1
        token_text = "".join(tokens)
        assert long_word in token_text or token_text == long_word

    @pytest.mark.asyncio
    async def test_streaming_respects_token_delay(self):
        """Test that streaming respects the configured token delay"""
        import time

        client = MockOlmClientV2(token_delay=0.01)  # Small but measurable delay
        messages = [{"role": "user", "content": "Hello world"}]

        result = await client.generate(messages, "test-model", stream=True)

        start_time = time.time()
        chunk_count = 0
        async for chunk in result:
            chunk_count += 1
            if chunk_count > 2:  # Skip first chunk, check after a few content chunks
                break

        elapsed = time.time() - start_time
        # Should take at least some time due to delays (very loose check)
        assert elapsed >= 0.005  # At least half the expected delay time

    @pytest.mark.asyncio
    async def test_streaming_zero_delay(self):
        """Test that streaming with zero delay works quickly"""
        import time

        client = MockOlmClientV2(token_delay=0)
        messages = [{"role": "user", "content": "Quick response"}]

        result = await client.generate(messages, "test-model", stream=True)

        start_time = time.time()
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        elapsed = time.time() - start_time

        # Should complete quickly with zero delay
        assert elapsed < 0.1  # Should be much faster than with delay
        assert len(chunks) >= 3  # Still should produce multiple chunks

    def test_usage_calculation_accuracy(self):
        """Test that usage token counts are calculated reasonably"""
        client = MockOlmClientV2(token_delay=0)
        messages = [{"role": "user", "content": "Calculate tokens"}]

        result = asyncio.run(client.generate(messages, "test-model", stream=False))

        usage = result["usage"]
        content = result["choices"][0]["message"]["content"]
        expected_completion_tokens = len(content.split())

        # Mock uses word count as completion tokens
        assert usage["completion_tokens"] == expected_completion_tokens
        assert usage["prompt_tokens"] == 10  # Mock constant
        assert usage["total_tokens"] == 10 + expected_completion_tokens

    @pytest.mark.asyncio
    async def test_concurrent_usage(self):
        """Test that multiple concurrent calls work correctly"""
        client = MockOlmClientV2(token_delay=0)
        messages = [{"role": "user", "content": "Concurrent test"}]

        # Create multiple concurrent requests
        tasks = [
            client.generate(messages, f"model-{i}", stream=False) for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed and have correct format
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["model"] == f"model-{i}"
            assert result["object"] == "chat.completion"
            assert "choices" in result

    @pytest.mark.asyncio
    async def test_streaming_and_non_streaming_consistency(self):
        """Test that streaming and non-streaming return equivalent content"""
        responses = ["Consistent response test"]
        client = MockOlmClientV2(responses=responses, token_delay=0)
        messages = [{"role": "user", "content": "test"}]

        # Non-streaming
        non_stream_result = await client.generate(messages, "test-model", stream=False)
        non_stream_content = non_stream_result["choices"][0]["message"]["content"]

        # Reset response index
        client.response_index = 0

        # Streaming
        stream_result = await client.generate(messages, "test-model", stream=True)
        stream_content = ""
        async for chunk in stream_result:
            if "content" in chunk["choices"][0]["delta"]:
                stream_content += chunk["choices"][0]["delta"]["content"]

        # Content should be equivalent
        assert non_stream_content == stream_content

    def test_api_url_parameter_ignored(self):
        """Test that api_url parameter is accepted but ignored"""
        client = MockOlmClientV2(api_url="http://example.com")
        # Should initialize successfully (api_url is ignored in mock)
        assert isinstance(client, MockOlmClientV2)

    @pytest.mark.asyncio
    async def test_empty_messages_list(self):
        """Test handling of empty messages list"""
        client = MockOlmClientV2(token_delay=0)

        result = await client.generate([], "test-model", stream=False)

        # Should still return valid response
        assert isinstance(result, dict)
        assert result["object"] == "chat.completion"
        assert "choices" in result

    @pytest.mark.asyncio
    async def test_message_content_ignored_in_mock(self):
        """Test that message content doesn't affect mock response selection"""
        client = MockOlmClientV2(responses=["Fixed response"], token_delay=0)

        # Different message contents should get same response
        messages1 = [{"role": "user", "content": "First message"}]
        messages2 = [{"role": "user", "content": "Completely different message"}]

        result1 = await client.generate(messages1, "test-model", stream=False)
        client.response_index = 0  # Reset to get same response
        result2 = await client.generate(messages2, "test-model", stream=False)

        assert (
            result1["choices"][0]["message"]["content"]
            == result2["choices"][0]["message"]["content"]
        )
