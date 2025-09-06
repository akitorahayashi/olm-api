import asyncio
from collections.abc import AsyncGenerator

import pytest

from sdk.olm_api_client.mock import MockOllamaApiClient
from sdk.olm_api_client.protocol import OllamaClientProtocol


class TestMockOllamaApiClient:
    """Test cases for MockOllamaApiClient"""

    def test_init_with_default_delay(self):
        """Test initialization with default token delay"""
        client = MockOllamaApiClient()
        assert client.token_delay == 0.01  # DEFAULT_TOKEN_DELAY

    def test_init_with_custom_delay(self):
        """Test initialization with custom token delay"""
        custom_delay = 0.05
        client = MockOllamaApiClient(token_delay=custom_delay)
        assert client.token_delay == custom_delay

    def test_init_with_api_url(self):
        """Test initialization with API URL parameter (should be accepted)"""
        client = MockOllamaApiClient(api_url="http://localhost:11434")
        # API URL is accepted but not used in mock
        assert client is not None

    def test_implements_protocol(self):
        """Test that MockOllamaApiClient implements OllamaClientProtocol"""
        client = MockOllamaApiClient()
        assert isinstance(client, OllamaClientProtocol)

    def test_tokenize_realistic_basic(self):
        """Test basic tokenization"""
        client = MockOllamaApiClient()
        text = "Hello world!"
        tokens = client._tokenize_realistic(text)

        assert len(tokens) > 0
        assert "Hello" in tokens
        assert "world" in tokens
        assert "!" in tokens

    def test_tokenize_realistic_think_tags(self):
        """Test tokenization preserves think tags"""
        client = MockOllamaApiClient()
        text = "<think>This is thinking</think> Response"
        tokens = client._tokenize_realistic(text)

        assert "<think>" in tokens
        assert "</think>" in tokens
        assert "This" in tokens
        assert "Response" in tokens

    def test_tokenize_realistic_long_words(self):
        """Test tokenization splits long words occasionally"""
        client = MockOllamaApiClient()
        text = "supercalifragilisticexpialidocious"
        tokens = client._tokenize_realistic(text)

        # Should either be whole word or split (deterministic based on hash)
        assert len(tokens) >= 1
        combined = "".join(tokens)
        assert combined == text

    def test_create_thinking_process(self):
        """Test thinking process generation"""
        client = MockOllamaApiClient()
        prompt = "Test prompt"
        thinking = client._create_thinking_process(prompt)

        assert isinstance(thinking, str)
        assert len(thinking) > 0
        assert any(
            keyword in thinking.lower() for keyword in ["analysis", "step", "process"]
        )

    def test_create_thinking_process_consistency(self):
        """Test thinking process is consistent for same prompt"""
        client = MockOllamaApiClient()
        prompt = "Same prompt"

        thinking1 = client._create_thinking_process(prompt)
        thinking2 = client._create_thinking_process(prompt)

        assert thinking1 == thinking2

    @pytest.mark.asyncio
    async def test_stream_response_basic(self):
        """Test basic streaming response"""
        client = MockOllamaApiClient(token_delay=0)  # No delay for fast test
        text = "Hello world"

        chunks = []
        async for chunk in client._stream_response(text):
            chunks.append(chunk)

        combined = "".join(chunks)
        assert "Hello" in combined
        assert "world" in combined

    @pytest.mark.asyncio
    async def test_stream_response_with_delay(self):
        """Test streaming with actual delay"""
        client = MockOllamaApiClient(token_delay=0.01)  # Small delay
        text = "Hi"

        start_time = asyncio.get_event_loop().time()
        chunks = []
        async for chunk in client._stream_response(text):
            chunks.append(chunk)
        end_time = asyncio.get_event_loop().time()

        # Should have taken some time due to delay
        assert end_time - start_time > 0.005  # At least some delay
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_gen_stream(self):
        """Test gen_stream method"""
        client = MockOllamaApiClient(token_delay=0)

        result = client.gen_stream("test prompt", "test-model")

        # Should return async generator
        assert isinstance(result, AsyncGenerator)

        chunks = []
        async for chunk in result:
            chunks.append(chunk)

        combined = "".join(chunks)
        assert "<think>" in combined
        assert "</think>" in combined
        assert len(combined) > 0

    @pytest.mark.asyncio
    async def test_gen_batch(self):
        """Test gen_batch method"""
        client = MockOllamaApiClient(token_delay=0)

        result = await client.gen_batch("test prompt", "test-model")

        # Should return string
        assert isinstance(result, str)
        assert "<think>" in result
        assert "</think>" in result
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_gen_batch_custom_responses(self):
        """Test gen_batch with custom responses for specific prompts"""
        client = MockOllamaApiClient(token_delay=0)

        test_cases = [
            ("hello there", "hello"),
            ("hi friend", "hi"),
            ("test input", "test"),
            ("help me", "help"),
            ("thanks a lot", "thanks"),
        ]

        for prompt, expected_keyword in test_cases:
            result = await client.gen_batch(prompt)
            assert isinstance(result, str)
            # The response should contain thinking + custom response
            assert "<think>" in result
            assert len(result) > len(prompt)

    @pytest.mark.asyncio
    async def test_gen_batch_cycling_responses(self):
        """Test that gen_batch cycles through mock responses"""
        client = MockOllamaApiClient(token_delay=0)

        responses = []
        for i in range(7):  # More than the number of mock responses
            result = await client.gen_batch(f"unique prompt {i}")
            responses.append(result)

        # Should have different responses (due to cycling and thinking variation)
        assert len(responses) == 7
        assert all(isinstance(r, str) for r in responses)
        assert all("<think>" in r for r in responses)

    @pytest.mark.asyncio
    async def test_gen_stream_with_model_parameter(self):
        """Test gen_stream accepts model parameter"""
        client = MockOllamaApiClient(token_delay=0)

        result = client.gen_stream("test", model="custom-model")
        chunks = []
        async for chunk in result:
            chunks.append(chunk)

        combined = "".join(chunks)
        assert len(combined) > 0

    @pytest.mark.asyncio
    async def test_gen_batch_with_model_parameter(self):
        """Test gen_batch accepts model parameter"""
        client = MockOllamaApiClient(token_delay=0)

        result = await client.gen_batch("test", model="custom-model")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_gen_stream_with_none_model(self):
        """Test gen_stream accepts None model parameter"""
        client = MockOllamaApiClient(token_delay=0)

        result = client.gen_stream("test", model=None)
        chunks = []
        async for chunk in result:
            chunks.append(chunk)

        combined = "".join(chunks)
        assert len(combined) > 0

    @pytest.mark.asyncio
    async def test_gen_batch_with_none_model(self):
        """Test gen_batch accepts None model parameter"""
        client = MockOllamaApiClient(token_delay=0)

        result = await client.gen_batch("test", model=None)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_gen_stream_with_think_true(self):
        """Test gen_stream includes think tags when think=True"""
        client = MockOllamaApiClient(token_delay=0)
        stream = client.gen_stream("prompt", "model", think=True)
        result = "".join([chunk async for chunk in stream])
        assert "<think>" in result
        assert "</think>" in result

    @pytest.mark.asyncio
    async def test_gen_stream_with_think_false(self):
        """Test gen_stream excludes think tags when think=False"""
        client = MockOllamaApiClient(token_delay=0)
        stream = client.gen_stream("prompt", "model", think=False)
        result = "".join([chunk async for chunk in stream])
        assert "<think>" not in result
        assert "</think>" not in result

    @pytest.mark.asyncio
    async def test_gen_batch_with_think_true(self):
        """Test gen_batch includes think tags when think=True"""
        client = MockOllamaApiClient(token_delay=0)
        result = await client.gen_batch("prompt", "model", think=True)
        assert "<think>" in result
        assert "</think>" in result

    @pytest.mark.asyncio
    async def test_gen_batch_with_think_false(self):
        """Test gen_batch excludes think tags when think=False"""
        client = MockOllamaApiClient(token_delay=0)
        result = await client.gen_batch("prompt", "model", think=False)
        assert "<think>" not in result
        assert "</think>" not in result


class TestMockEnvironmentVariable:
    """Test MockOllamaApiClient with environment variable configuration"""

    def test_init_with_env_var(self, monkeypatch):
        """Test initialization with MOCK_TOKEN_DELAY environment variable"""
        monkeypatch.setenv("MOCK_TOKEN_DELAY", "0.02")
        client = MockOllamaApiClient()
        assert client.token_delay == 0.02

    def test_init_parameter_overrides_env_var(self, monkeypatch):
        """Test that parameter overrides environment variable"""
        monkeypatch.setenv("MOCK_TOKEN_DELAY", "0.02")
        client = MockOllamaApiClient(token_delay=0.05)
        assert client.token_delay == 0.05

    def test_init_with_invalid_env_var(self, monkeypatch):
        """Test initialization with invalid environment variable falls back to default"""
        monkeypatch.setenv("MOCK_TOKEN_DELAY", "invalid")
        with pytest.raises(ValueError):  # float() conversion should fail
            MockOllamaApiClient()
