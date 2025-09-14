import asyncio
from collections.abc import AsyncGenerator

import pytest

from sdk.olm_api_client.v1.mock_client import MockOlmClientV1
from sdk.olm_api_client.v1.protocol import OlmClientV1Protocol


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

        combined = "".join(chunks)
        assert "Hello" in combined
        assert "world" in combined

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

        combined = "".join(chunks)
        assert len(combined) > 0
        assert "Hello" in combined  # Check for part of the default response

    @pytest.mark.asyncio
    async def test_generate_batch(self):
        """Test generate method without streaming"""
        client = MockOlmClientV1(token_delay=0)

        result = await client.generate("test prompt", "test-model", stream=False)

        # Should return string
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Hello" in result  # Check for part of the default response

    def test_init_with_custom_responses(self):
        """Test initialization with custom responses parameter"""
        custom_responses = ["Response A", "Response B", "Response C"]
        client = MockOlmClientV1(responses=custom_responses)
        assert client.mock_responses == custom_responses

    def test_init_without_custom_responses(self):
        """Test initialization without custom responses uses defaults"""
        client = MockOlmClientV1()
        # Should have default responses
        assert len(client.mock_responses) == 5
        assert "Hello! How can I help you today?" in client.mock_responses

    @pytest.mark.asyncio
    async def test_generate_with_custom_responses(self):
        """Test generate uses custom responses array"""
        custom_responses = ["カスタムレスポンス1", "Custom response 2", "Réponse 3"]
        client = MockOlmClientV1(responses=custom_responses, token_delay=0)

        for i, expected_response in enumerate(custom_responses):
            result = await client.generate(f"test prompt {i}", "test-model")
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_generate_with_custom_responses(self):
        """Test generate uses custom responses array"""
        custom_responses = ["Short response", "Longer custom response"]
        client = MockOlmClientV1(responses=custom_responses, token_delay=0)

        # Test first response
        result = await client.generate("test 1", "test-model", stream=True)
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        result1 = "".join(chunks)
        assert result1 == custom_responses[0]

        # Test second response
        result = await client.generate("test 2", "test-model", stream=True)
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        result2 = "".join(chunks)
        assert result2 == custom_responses[1]

    @pytest.mark.asyncio
    async def test_response_cycling_with_custom_responses(self):
        """Test that custom responses cycle correctly"""
        custom_responses = ["First", "Second", "Third"]
        client = MockOlmClientV1(responses=custom_responses, token_delay=0)

        results = []
        for i in range(6):  # Test two full cycles
            result = await client.generate(f"test {i}", "test-model")
            results.append(result)

        # Should cycle through responses: First, Second, Third, First, Second, Third
        expected = custom_responses * 2
        assert results == expected

    @pytest.mark.asyncio
    async def test_response_cycling_with_default_responses(self):
        """Test that default responses cycle correctly"""
        client = MockOlmClientV1(token_delay=0)

        results = []
        for i in range(7):  # More than the number of default responses (5)
            result = await client.generate(f"unique prompt {i}", "test-model")
            results.append(result)

        # Should have cycled through all 5 default responses and started again
        assert len(results) == 7
        assert all(isinstance(r, str) for r in results)
        # First 5 should be the default responses, then it repeats
        assert results[0] == client.mock_responses[0]
        assert results[5] == client.mock_responses[0]  # Cycled back

    @pytest.mark.asyncio
    async def test_simplified_api_usage(self):
        """Test that the simplified API usage works as expected"""
        client = MockOlmClientV1(api_url="http://localhost:11434", token_delay=0)

        result = await client.generate("test prompt", "some-model", stream=False)
        assert isinstance(result, str)
        assert len(result) > 0

        # Streaming should also work
        stream_result = await client.generate("test", "some-model", stream=True)
        chunks = []
        async for chunk in stream_result:
            chunks.append(chunk)
        combined = "".join(chunks)
        assert len(combined) > 0

    @pytest.mark.asyncio
    async def test_mixed_parameters(self):
        """Test initialization with mixed custom and existing parameters"""
        custom_responses = ["Test response 1", "Test response 2"]
        client = MockOlmClientV1(
            api_url="http://localhost:11434",
            token_delay=0.02,
            responses=custom_responses,
        )

        assert client.token_delay == 0.02
        assert client.mock_responses == custom_responses

        result = await client.generate("test", "some-model", stream=False)
        assert result in custom_responses

        # Note: Dictionary and callable responses are not currently supported in v1 mock client
        # These tests are disabled until the feature is implemented
        response2 = await client.generate("I have a question for you.", "test-model")
        assert response2 == "This is the answer."

        # Test no match - should use default response
        response3 = await client.generate("Some other prompt", "test-model")
        assert response3 == client.default_responses[0]

        # Test another no match - should cycle default responses
        response4 = await client.generate("Another prompt", "test-model")
        assert response4 == client.default_responses[1]

    # Note: Dictionary and callable responses are not currently supported in v1 mock client
    # These tests are disabled until the feature is implemented

    def test_init_with_empty_list_raises_error(self):
        """Test that initializing with an empty list still raises ValueError."""
        with pytest.raises(ValueError, match="responses must be a non-empty list"):
            MockOlmClientV1(responses=[])

    def test_init_with_non_string_list_raises_error(self):
        """Test that initializing with non-string list raises TypeError."""
        with pytest.raises(TypeError, match="all responses must be str"):
            MockOlmClientV1(responses=["valid", 123, "also valid"])


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
        with pytest.raises(ValueError):  # float() conversion should fail
            MockOlmClientV1()
