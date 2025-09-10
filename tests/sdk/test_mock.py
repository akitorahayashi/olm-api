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

    def test_tokenize_realistic_long_words(self):
        """Test tokenization splits long words occasionally"""
        client = MockOllamaApiClient()
        text = "supercalifragilisticexpialidocious"
        tokens = client._tokenize_realistic(text)

        # Should either be whole word or split (deterministic based on hash)
        assert len(tokens) >= 1
        combined = "".join(tokens)
        assert combined == text

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
        assert len(combined) > 0
        assert "Hello" in combined  # Check for part of the default response

    @pytest.mark.asyncio
    async def test_gen_batch(self):
        """Test gen_batch method"""
        client = MockOllamaApiClient(token_delay=0)

        result = await client.gen_batch("test prompt", "test-model")

        # Should return string
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Hello" in result  # Check for part of the default response

    def test_init_with_custom_responses(self):
        """Test initialization with custom responses parameter"""
        custom_responses = ["Response A", "Response B", "Response C"]
        client = MockOllamaApiClient(responses=custom_responses)
        assert client.mock_responses == custom_responses

    def test_init_without_custom_responses(self):
        """Test initialization without custom responses uses defaults"""
        client = MockOllamaApiClient()
        # Should have default responses
        assert len(client.mock_responses) == 5
        assert "Hello! How can I help you today?" in client.mock_responses

    @pytest.mark.asyncio
    async def test_gen_batch_with_custom_responses(self):
        """Test gen_batch uses custom responses array"""
        custom_responses = ["カスタムレスポンス1", "Custom response 2", "Réponse 3"]
        client = MockOllamaApiClient(responses=custom_responses, token_delay=0)

        for i, expected_response in enumerate(custom_responses):
            result = await client.gen_batch(f"test prompt {i}", "test-model")
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_gen_stream_with_custom_responses(self):
        """Test gen_stream uses custom responses array"""
        custom_responses = ["Short response", "Longer custom response"]
        client = MockOllamaApiClient(responses=custom_responses, token_delay=0)

        # Test first response
        chunks = []
        async for chunk in client.gen_stream("test 1", "test-model"):
            chunks.append(chunk)
        result1 = "".join(chunks)
        assert result1 == custom_responses[0]

        # Test second response
        chunks = []
        async for chunk in client.gen_stream("test 2", "test-model"):
            chunks.append(chunk)
        result2 = "".join(chunks)
        assert result2 == custom_responses[1]

    @pytest.mark.asyncio
    async def test_response_cycling_with_custom_responses(self):
        """Test that custom responses cycle correctly"""
        custom_responses = ["First", "Second", "Third"]
        client = MockOllamaApiClient(responses=custom_responses, token_delay=0)

        results = []
        for i in range(6):  # Test two full cycles
            result = await client.gen_batch(f"test {i}", "test-model")
            results.append(result)

        # Should cycle through responses: First, Second, Third, First, Second, Third
        expected = custom_responses * 2
        assert results == expected

    @pytest.mark.asyncio
    async def test_response_cycling_with_default_responses(self):
        """Test that default responses cycle correctly"""
        client = MockOllamaApiClient(token_delay=0)

        results = []
        for i in range(7):  # More than the number of default responses (5)
            result = await client.gen_batch(f"unique prompt {i}", "test-model")
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
        client = MockOllamaApiClient(api_url="http://localhost:11434", token_delay=0)

        result = await client.gen_batch("test prompt", "some-model")
        assert isinstance(result, str)
        assert len(result) > 0

        # Streaming should also work
        chunks = []
        async for chunk in client.gen_stream("test", "some-model"):
            chunks.append(chunk)
        combined = "".join(chunks)
        assert len(combined) > 0

    @pytest.mark.asyncio
    async def test_mixed_parameters(self):
        """Test initialization with mixed custom and existing parameters"""
        custom_responses = ["Test response 1", "Test response 2"]
        client = MockOllamaApiClient(
            api_url="http://localhost:11434",
            token_delay=0.02,
            responses=custom_responses,
        )

        assert client.token_delay == 0.02
        assert client.mock_responses == custom_responses

        result = await client.gen_batch("test", "some-model")
        assert result in custom_responses

    @pytest.mark.asyncio
    async def test_gen_batch_with_dict_responses(self):
        """Test gen_batch uses dictionary to map prompts to responses."""
        prompt_map = {
            "Hello": "Hi there!",
            "question": "This is the answer.",
        }
        client = MockOllamaApiClient(responses=prompt_map, token_delay=0)

        # Test exact match
        response1 = await client.gen_batch("Hello", "test-model")
        assert response1 == "Hi there!"

        # Test partial match
        response2 = await client.gen_batch("I have a question for you.", "test-model")
        assert response2 == "This is the answer."

        # Test no match - should use default response
        response3 = await client.gen_batch("Some other prompt", "test-model")
        assert response3 == client.default_responses[0]

        # Test another no match - should cycle default responses
        response4 = await client.gen_batch("Another prompt", "test-model")
        assert response4 == client.default_responses[1]

    @pytest.mark.asyncio
    async def test_gen_batch_with_callable_response(self):
        """Test gen_batch uses a callable to generate responses."""

        def response_generator(prompt: str, model_name: str) -> str:
            if "hello" in prompt.lower():
                return f"Response for hello from {model_name}"
            return "Default callable response"

        client = MockOllamaApiClient(responses=response_generator, token_delay=0)

        response1 = await client.gen_batch("Hello there", "model-1")
        assert response1 == "Response for hello from model-1"

        response2 = await client.gen_batch("Some other prompt", "model-2")
        assert response2 == "Default callable response"

    def test_init_with_empty_list_raises_error(self):
        """Test that initializing with an empty list still raises ValueError."""
        with pytest.raises(ValueError, match="responses must be a non-empty list"):
            MockOllamaApiClient(responses=[])

    def test_init_with_non_string_list_raises_error(self):
        """Test that initializing with non-string list raises TypeError."""
        with pytest.raises(TypeError, match="all responses must be str"):
            MockOllamaApiClient(responses=["valid", 123, "also valid"])


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


class TestMockStreamingWithDifferentResponseTypes:
    """Test streaming behavior with dictionary and callable responses"""

    @pytest.mark.asyncio
    async def test_gen_stream_with_dictionary_response(self):
        """Test gen_stream with dictionary mapping responses."""
        responses_map = {"hello": "Hi there!", "test": "Test response"}
        client = MockOllamaApiClient(responses=responses_map, token_delay=0)

        # Test exact match
        chunks = []
        async for chunk in client.gen_stream("hello", "test-model"):
            chunks.append(chunk)
        assert "".join(chunks) == "Hi there!"

        # Test partial match
        chunks = []
        async for chunk in client.gen_stream("testing something", "test-model"):
            chunks.append(chunk)
        assert "".join(chunks) == "Test response"

    @pytest.mark.asyncio
    async def test_gen_stream_with_callable_response(self):
        """Test gen_stream with callable response generator."""

        def response_generator(prompt: str, model_name: str) -> str:
            return f"Generated-{model_name}-{len(prompt)}"

        client = MockOllamaApiClient(responses=response_generator, token_delay=0)
        chunks = []
        async for chunk in client.gen_stream("test", "model1"):
            chunks.append(chunk)
        assert "".join(chunks) == "Generated-model1-4"

    @pytest.mark.asyncio
    async def test_gen_stream_with_non_string_callable_response(self):
        """Test gen_stream handles non-string callable responses."""

        def response_generator(prompt: str, model_name: str) -> int:
            return 42  # Return non-string

        client = MockOllamaApiClient(responses=response_generator, token_delay=0)
        chunks = []
        async for chunk in client.gen_stream("test", "model1"):
            chunks.append(chunk)
        assert "".join(chunks) == "42"  # Should be converted to string
