from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sdk.olm_api_client.client import OllamaApiClient
from sdk.olm_api_client.protocol import OllamaClientProtocol


class TestOllamaApiClient:
    """Test cases for OllamaApiClient"""

    def test_init_success(self):
        """Test successful initialization with API URL"""
        api_url = "http://localhost:11434"
        client = OllamaApiClient(api_url=api_url)
        assert client.api_url == api_url
        assert client.generate_endpoint == f"{api_url}/api/v1/generate"

    def test_init_without_api_url_raises_error(self):
        """Test initialization without required api_url raises TypeError"""
        with pytest.raises(TypeError):
            OllamaApiClient()

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from API URL"""
        api_url = "http://localhost:11434/"
        client = OllamaApiClient(api_url=api_url)
        assert client.api_url == "http://localhost:11434"

    def test_implements_protocol(self):
        """Test that OllamaApiClient implements OllamaClientProtocol"""
        client = OllamaApiClient(api_url="http://localhost:11434")
        assert isinstance(client, OllamaClientProtocol)

    @pytest.mark.asyncio
    async def test_gen_stream(self):
        """Test gen_stream method"""
        client = OllamaApiClient(api_url="http://localhost:11434")

        with patch.object(client, "_stream_response") as mock_stream:
            mock_stream.return_value = async_generator_mock(["Hello", " world"])

            result = client.gen_stream("test prompt", "test-model")

            # Verify it returns an async generator
            assert hasattr(result, "__aiter__")

            # Collect results
            chunks = []
            async for chunk in result:
                chunks.append(chunk)

            assert chunks == ["Hello", " world"]
            mock_stream.assert_called_once_with("test prompt", "test-model")

    @pytest.mark.asyncio
    async def test_gen_batch(self):
        """Test gen_batch method"""
        client = OllamaApiClient(api_url="http://localhost:11434")

        with patch.object(client, "_non_stream_response") as mock_non_stream:
            mock_non_stream.return_value = "Complete response"

            result = await client.gen_batch("test prompt", "test-model")

            assert result == "Complete response"
            mock_non_stream.assert_called_once_with("test prompt", "test-model")


async def async_generator_mock(items):
    """Helper function to create async generator mock"""
    for item in items:
        yield item


class TestIntegrationWithMock:
    """Integration tests using httpx mocking"""

    @pytest.mark.asyncio
    async def test_stream_response_success(self):
        """Test successful streaming response"""
        client = OllamaApiClient(api_url="http://localhost:11434")

        mock_response_data = [
            'data: {"response": "Hello"}\n',
            'data: {"response": " world"}\n',
            'data: {"response": "!"}\n',
        ]

        # Create mock response object
        mock_response = MagicMock()
        mock_response.aiter_lines.return_value = async_generator_mock(
            mock_response_data
        )
        mock_response.raise_for_status = MagicMock()

        # Create mock stream context
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        # Create mock client with proper spec
        mock_client = MagicMock()
        mock_client.stream.return_value = mock_stream_context

        # Create mock async client context
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value = mock_client
        mock_async_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_async_client):
            result = client._stream_response("test prompt", "test-model")
            chunks = []
            async for chunk in result:
                chunks.append(chunk)

            assert chunks == ["Hello", " world", "!"]

    @pytest.mark.asyncio
    async def test_non_stream_response_success(self):
        """Test successful non-streaming response"""
        client = OllamaApiClient(api_url="http://localhost:11434")

        # Create mock response object
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Complete response text"}
        mock_response.raise_for_status = MagicMock()

        # Create mock client
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        # Create mock async client context
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value = mock_client
        mock_async_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_async_client):
            result = await client._non_stream_response("test prompt", "test-model")

            assert result == "Complete response text"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_response_handles_request_error(self):
        """Test that streaming handles httpx.RequestError"""
        client = OllamaApiClient(api_url="http://localhost:11434")

        # Create mock client that raises an exception
        mock_client = MagicMock()
        mock_client.stream.side_effect = httpx.RequestError("Connection failed")

        # Create mock async client context
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value = mock_client
        mock_async_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_async_client):
            with pytest.raises(httpx.RequestError):
                result = client._stream_response("test prompt", "test-model")
                async for _ in result:
                    pass

    @pytest.mark.asyncio
    async def test_non_stream_response_handles_request_error(self):
        """Test that non-streaming handles httpx.RequestError"""
        client = OllamaApiClient(api_url="http://localhost:11434")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.RequestError("Connection failed")

            with pytest.raises(httpx.RequestError):
                await client._non_stream_response("test prompt", "test-model")
