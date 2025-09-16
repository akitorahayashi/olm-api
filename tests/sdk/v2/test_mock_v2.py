import os
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from olm_api_sdk.v2.mock_client import MockOlmClientV2
from olm_api_sdk.v2.protocol import OlmClientV2Protocol


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
        assert len(client.fallback_responses) == 5  # DEFAULT_RESPONSES length

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
        assert client.fallback_responses == custom_responses

    def test_init_empty_responses_raises_error(self):
        """Test initialization with empty responses raises ValueError"""
        with pytest.raises(ValueError, match="The responses sequence cannot be empty"):
            MockOlmClientV2(responses=[])

    def test_init_non_string_responses_raises_error(self):
        """Test initialization with non-string responses raises TypeError"""
        with pytest.raises(
            TypeError, match="All items in the responses sequence must be strings"
        ):
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


class TestKeyedResponsesV2:
    """Tests for keyed response functionality in MockOlmClientV2."""

    @pytest.mark.asyncio
    async def test_keyed_response_batch(self):
        """Test that a keyed response is returned for a matching prompt."""
        keyed_responses = {"ping": "pong", "hello": "world"}
        client = MockOlmClientV2(responses=keyed_responses, token_delay=0)

        messages = [{"role": "user", "content": "ping"}]
        result = await client.generate(messages, "test-model")
        assert result["choices"][0]["message"]["content"] == "pong"

        messages = [{"role": "user", "content": "hello"}]
        result = await client.generate(messages, "test-model")
        assert result["choices"][0]["message"]["content"] == "world"

    @pytest.mark.asyncio
    async def test_keyed_response_streaming(self):
        """Test that a keyed response is streamed correctly."""
        keyed_responses = {"stream_test": "streaming pong"}
        client = MockOlmClientV2(responses=keyed_responses, token_delay=0)

        messages = [{"role": "user", "content": "stream_test"}]
        result = await client.generate(messages, "test-model", stream=True)
        chunks = [chunk async for chunk in result]

        # Extract content from streaming chunks
        content = ""
        for chunk in chunks:
            if "content" in chunk["choices"][0]["delta"]:
                content += chunk["choices"][0]["delta"]["content"]

        assert content == "streaming pong"

    @pytest.mark.asyncio
    async def test_fallback_for_unmatched_prompt(self):
        """Test that fallback responses are used when prompt does not match a key."""
        keyed_responses = {"ping": "pong"}
        client = MockOlmClientV2(responses=keyed_responses, token_delay=0)

        messages = [{"role": "user", "content": "unmatched_prompt"}]
        result = await client.generate(messages, "test-model")
        assert result["choices"][0]["message"]["content"] in client.fallback_responses

    def test_init_with_invalid_dict(self):
        """Test that initializing with a non-string key/value in dict raises TypeError."""
        with pytest.raises(
            TypeError,
            match="All keys and values in the responses dictionary must be strings",
        ):
            MockOlmClientV2(responses={"valid_key": 123})

        with pytest.raises(
            TypeError,
            match="All keys and values in the responses dictionary must be strings",
        ):
            MockOlmClientV2(responses={123: "valid_value"})
