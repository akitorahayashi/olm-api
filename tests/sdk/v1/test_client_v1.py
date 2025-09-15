from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sdk.olm_api_client.v1.client import OlmApiClientV1
from sdk.olm_api_client.v1.protocol import OlmClientV1Protocol


class TestOlmApiClientV1:
    """Test cases for OlmApiClientV1"""

    def test_init_success(self):
        """Test successful initialization with API URL"""
        api_url = "http://localhost:11434"
        client = OlmApiClientV1(api_url=api_url)
        assert client.api_url == api_url
        assert client.generate_endpoint == f"{api_url}/api/v1/chat"

    def test_init_without_api_url_raises_error(self):
        """Test initialization without required api_url raises TypeError"""
        with pytest.raises(TypeError):
            OlmApiClientV1()

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from API URL"""
        api_url = "http://localhost:11434/"
        client = OlmApiClientV1(api_url=api_url)
        assert client.api_url == "http://localhost:11434"

    def test_implements_protocol(self):
        """Test that OlmApiClientV1 implements OlmClientV1Protocol"""
        client = OlmApiClientV1(api_url="http://localhost:11434")
        assert isinstance(client, OlmClientV1Protocol)

    @pytest.mark.asyncio
    async def test_generate_streaming(self):
        """Test generate method with streaming"""
        client = OlmApiClientV1(api_url="http://localhost:11434")

        mock_chunks = [
            {"think": "thinking1", "content": "Hello", "response": "Hello"},
            {"think": "thinking2", "content": " world", "response": "Hello world"},
        ]

        with patch.object(client, "_stream_response") as mock_stream:
            mock_stream.return_value = async_generator_mock(mock_chunks)

            result = await client.generate("test prompt", "test-model", stream=True)

            # Verify it returns an async generator
            assert hasattr(result, "__aiter__")

            # Collect results
            chunks = []
            async for chunk in result:
                chunks.append(chunk)

            assert chunks == mock_chunks
            mock_stream.assert_called_once_with("test prompt", "test-model", None)

    @pytest.mark.asyncio
    async def test_generate_non_streaming(self):
        """Test generate method without streaming"""
        client = OlmApiClientV1(api_url="http://localhost:11434")

        mock_response = {
            "think": "some thinking",
            "content": "Complete response",
            "response": "Complete response",
        }

        with patch.object(client, "_non_stream_response") as mock_non_stream:
            mock_non_stream.return_value = mock_response

            result = await client.generate("test prompt", "test-model", stream=False)

            assert result == mock_response
            assert "think" in result
            assert "content" in result
            assert "response" in result
            mock_non_stream.assert_called_once_with("test prompt", "test-model", None)


async def async_generator_mock(items):
    """Helper function to create async generator mock"""
    for item in items:
        yield item


class TestIntegrationWithMock:
    """Integration tests using httpx mocking"""

    @pytest.mark.asyncio
    async def test_stream_response_success(self):
        """Test successful streaming response"""
        client = OlmApiClientV1(api_url="http://localhost:11434")

        mock_response_data = [
            'data: {"think": "thinking1", "content": "Hello", "response": "Hello"}\n',
            'data: {"think": "thinking2", "content": " world", "response": "Hello world"}\n',
            'data: {"think": "thinking3", "content": "!", "response": "Hello world!"}\n',
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

            assert len(chunks) == 3
            assert chunks[0]["content"] == "Hello"
            assert chunks[1]["content"] == " world"
            assert chunks[2]["content"] == "!"
            assert all("think" in chunk for chunk in chunks)
            assert all("response" in chunk for chunk in chunks)

    @pytest.mark.asyncio
    async def test_non_stream_response_success(self):
        """Test successful non-streaming response"""
        client = OlmApiClientV1(api_url="http://localhost:11434")

        # Create mock response object
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "think": "some thinking process",
            "content": "Complete response text",
            "response": "Complete response text",
        }
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

            assert isinstance(result, dict)
            assert "think" in result
            assert "content" in result
            assert "response" in result
            assert result["content"] == "Complete response text"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_response_handles_request_error(self):
        """Test that streaming handles httpx.RequestError"""
        client = OlmApiClientV1(api_url="http://localhost:11434")

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
        client = OlmApiClientV1(api_url="http://localhost:11434")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.RequestError("Connection failed")

            with pytest.raises(httpx.RequestError):
                await client._non_stream_response("test prompt", "test-model")
