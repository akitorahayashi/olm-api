import asyncio
from collections.abc import AsyncGenerator

import pytest
from olm_api_sdk.v1.mock_client import DEFAULT_TOKEN_DELAY, MockOlmClientV1
from olm_api_sdk.v1.protocol import OlmClientV1Protocol


class TestMockOlmClientV1:
    """Test cases for MockOlmClientV1"""

    def test_init_with_default_delay(self):
        """Test initialization with default token delay"""
        client = MockOlmClientV1()
        assert client.token_delay == 0.01  # DEFAULT_TOKEN_DELAY

    def test_init_with_custom_delay(self):
        """Test initialization with custom token delay"""
        custom_delay = 0.05
        client = MockOlmClientV1(token_delay=custom_delay)
        assert client.token_delay == custom_delay

    def test_init_with_api_url(self):
        """Test initialization with API URL parameter (should be accepted)"""
        client = MockOlmClientV1(api_url="http://localhost:11434")
        # API URL is accepted but not used in mock
        assert client is not None

    def test_implements_protocol(self):
        """Test that MockOlmClientV1 implements OlmClientV1Protocol"""
        client = MockOlmClientV1()
        assert isinstance(client, OlmClientV1Protocol)

    def test_tokenize_realistic_basic(self):
        """Test basic tokenization"""
        client = MockOlmClientV1()
        text = "Hello world!"
        tokens = client._tokenize_realistic(text)

        assert len(tokens) > 0
        assert "Hello" in tokens
        assert "world" in tokens
        assert "!" in tokens

    def test_tokenize_realistic_long_words(self):
        """Test tokenization splits long words occasionally"""
        client = MockOlmClientV1()
        text = "supercalifragilisticexpialidocious"
        tokens = client._tokenize_realistic(text)

        # Should either be whole word or split (deterministic based on hash)
        assert len(tokens) >= 1
        combined = "".join(tokens)
        assert combined == text

    @pytest.mark.asyncio
    async def test_stream_response_basic(self):
        """Test basic streaming response"""
        client = MockOlmClientV1(token_delay=0)  # No delay for fast test
        text = "Hello world"

        chunks = []
        async for chunk in client._stream_response(text):
            chunks.append(chunk)

        # Each chunk should be a dict with the required structure
        assert all(isinstance(chunk, dict) for chunk in chunks)
        assert all(
            "think" in chunk and "content" in chunk and "response" in chunk
            for chunk in chunks
        )

        # Final content should contain the original text
        final_content = chunks[-1]["content"] if chunks else ""
        assert final_content == text

    @pytest.mark.asyncio
    async def test_stream_response_with_delay(self):
        """Test streaming with actual delay"""
        client = MockOlmClientV1(token_delay=0.01)  # Small delay
        text = "Hi"

        start_time = asyncio.get_event_loop().time()
        chunks = []
        async for chunk in client._stream_response(text):
            chunks.append(chunk)
        end_time = asyncio.get_event_loop().time()

        # Should have taken some time due to delay
        assert end_time - start_time > 0.005  # At least some delay
        assert len(chunks) > 0
        assert all(isinstance(chunk, dict) for chunk in chunks)

    @pytest.mark.asyncio
    async def test_generate_streaming(self):
        """Test generate method with streaming"""
        client = MockOlmClientV1(token_delay=0)

        result = await client.generate("test prompt", "test-model", stream=True)

        # Should return async generator
        assert isinstance(result, AsyncGenerator)

        chunks = []
        async for chunk in result:
            chunks.append(chunk)

        # Each chunk should be a dict
        assert all(isinstance(chunk, dict) for chunk in chunks)
        assert all(
            "think" in chunk and "content" in chunk and "response" in chunk
            for chunk in chunks
        )

        # Final content should contain expected text
        final_content = chunks[-1]["content"] if chunks else ""
        assert len(final_content) > 0
        assert final_content in client.fallback_responses

    @pytest.mark.asyncio
    async def test_generate_batch(self):
        """Test generate method without streaming"""
        client = MockOlmClientV1(token_delay=0)

        result = await client.generate("test prompt", "test-model", stream=False)

        # Should return dict with required structure
        assert isinstance(result, dict)
        assert "think" in result
        assert "content" in result
        assert "response" in result
        assert len(result["content"]) > 0
        assert result["content"] in client.fallback_responses

    def test_init_with_custom_responses(self):
        """Test initialization with custom responses parameter"""
        custom_responses = ["Response A", "Response B", "Response C"]
        client = MockOlmClientV1(responses=custom_responses)
        assert client.fallback_responses == custom_responses

    def test_init_without_custom_responses(self):
        """Test initialization without custom responses uses defaults"""
        client = MockOlmClientV1()
        # Should have default responses
        assert len(client.fallback_responses) == 5
        assert "Hello! How can I help you today?" in client.fallback_responses

    @pytest.mark.asyncio
    async def test_generate_with_custom_responses(self):
        """Test generate uses custom responses array"""
        custom_responses = ["カスタムレスポンス1", "Custom response 2", "Réponse 3"]
        client = MockOlmClientV1(responses=custom_responses, token_delay=0)

        for i, expected_response in enumerate(custom_responses):
            result = await client.generate(f"test prompt {i}", "test-model")
            assert isinstance(result, dict)
            assert result["content"] in custom_responses
            assert result["response"] in custom_responses

    @pytest.mark.asyncio
    async def test_generate_with_custom_responses_streaming(self):
        """Test generate uses custom responses array with streaming"""
        custom_responses = ["Short response", "Longer custom response"]
        client = MockOlmClientV1(responses=custom_responses, token_delay=0)

        # Test first response
        result = await client.generate("test 1", "test-model", stream=True)
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        result1 = chunks[-1]["content"] if chunks else ""
        assert result1 in custom_responses

        # Test second response
        result = await client.generate("test 2", "test-model", stream=True)
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        result2 = chunks[-1]["content"] if chunks else ""
        assert result2 in custom_responses

    def test_init_with_empty_list_raises_error(self):
        """Test that initializing with an empty list still raises ValueError."""
        with pytest.raises(ValueError, match="The responses sequence cannot be empty"):
            MockOlmClientV1(responses=[])

    def test_init_with_non_string_list_raises_error(self):
        """Test that initializing with non-string list raises TypeError."""
        with pytest.raises(
            TypeError, match="All items in the responses sequence must be strings"
        ):
            MockOlmClientV1(responses=["valid", 123, "also valid"])


class TestKeyedResponsesV1:
    """Tests for keyed response functionality in MockOlmClientV1."""

    @pytest.mark.asyncio
    async def test_keyed_response_batch(self):
        """Test that a keyed response is returned for a matching prompt."""
        keyed_responses = {"ping": "pong", "hello": "world"}
        client = MockOlmClientV1(responses=keyed_responses, token_delay=0)

        result = await client.generate("ping", "test-model")
        assert result["content"] == "pong"

        result = await client.generate("hello", "test-model")
        assert result["content"] == "world"

    @pytest.mark.asyncio
    async def test_keyed_response_streaming(self):
        """Test that a keyed response is streamed correctly."""
        keyed_responses = {"stream_test": "streaming pong"}
        client = MockOlmClientV1(responses=keyed_responses, token_delay=0)

        result = await client.generate("stream_test", "test-model", stream=True)
        chunks = [chunk async for chunk in result]
        final_content = chunks[-1]["content"] if chunks else ""

        assert final_content == "streaming pong"

    @pytest.mark.asyncio
    async def test_fallback_for_unmatched_prompt(self):
        """Test that fallback responses are used when prompt does not match a key."""
        keyed_responses = {"ping": "pong"}
        client = MockOlmClientV1(responses=keyed_responses, token_delay=0)

        result = await client.generate("unmatched_prompt", "test-model")
        assert result["content"] in client.fallback_responses

    def test_init_with_invalid_dict(self):
        """Test that initializing with a non-string key/value in dict raises TypeError."""
        with pytest.raises(
            TypeError,
            match="All keys and values in the responses dictionary must be strings",
        ):
            MockOlmClientV1(responses={"valid_key": 123})

        with pytest.raises(
            TypeError,
            match="All keys and values in the responses dictionary must be strings",
        ):
            MockOlmClientV1(responses={123: "valid_value"})


class TestMockEnvironmentVariable:
    """Test MockOlmClientV1 with environment variable configuration"""

    def test_init_with_env_var(self, monkeypatch):
        """Test initialization with MOCK_TOKEN_DELAY environment variable"""
        monkeypatch.setenv("MOCK_TOKEN_DELAY", "0.02")
        client = MockOlmClientV1()
        assert client.token_delay == 0.02

    def test_init_parameter_overrides_env_var(self, monkeypatch):
        """Test that parameter overrides environment variable"""
        monkeypatch.setenv("MOCK_TOKEN_DELAY", "0.02")
        client = MockOlmClientV1(token_delay=0.05)
        assert client.token_delay == 0.05

    def test_init_with_invalid_env_var(self, monkeypatch):
        """Test initialization with invalid environment variable falls back to default"""
        monkeypatch.setenv("MOCK_TOKEN_DELAY", "invalid")
        client = MockOlmClientV1()  # Should not raise, should fall back to default
        assert client.token_delay == DEFAULT_TOKEN_DELAY
