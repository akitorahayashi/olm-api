from unittest.mock import AsyncMock, patch

import pytest

from sdk.olm_api_client.local_client import OllamaLocalClient
from sdk.olm_api_client.protocol import OllamaClientProtocol


@pytest.fixture
def mock_ollama_client_instance():
    """
    Fixture that patches `ollama.AsyncClient` and yields a mock instance.
    This prevents the actual client from being created while allowing tests
    to configure the behavior of the instance's methods.
    """
    with patch("ollama.AsyncClient") as mock_class:
        mock_instance = AsyncMock()
        mock_class.return_value = mock_instance
        yield mock_instance


class TestOllamaLocalClient:
    """Test cases for OllamaLocalClient"""

    def test_implements_protocol(self):
        """Test that OllamaLocalClient implements OllamaClientProtocol"""
        client = OllamaLocalClient()
        assert isinstance(client, OllamaClientProtocol)

    @pytest.mark.asyncio
    async def test_gen_batch_success(self, mock_ollama_client_instance):
        """Test successful batch generation"""
        client = OllamaLocalClient()
        mock_ollama_client_instance.chat.return_value = {
            "message": {"content": "Test response"}
        }

        response = await client.gen_batch("test prompt", "test-model")
        assert response == "Test response"
        mock_ollama_client_instance.chat.assert_called_once_with(
            model="test-model",
            messages=[{"role": "user", "content": "test prompt"}],
            stream=False,
        )

    @pytest.mark.asyncio
    async def test_gen_stream_success(self, mock_ollama_client_instance):
        """Test successful stream generation"""

        async def mock_stream():
            yield {"message": {"content": "Hello"}}
            yield {"message": {"content": " "}}
            yield {"message": {"content": "World"}}

        client = OllamaLocalClient()
        mock_ollama_client_instance.chat.return_value = mock_stream()

        chunks = [
            chunk async for chunk in client.gen_stream("test prompt", "test-model")
        ]
        assert "".join(chunks) == "Hello World"
        mock_ollama_client_instance.chat.assert_called_once_with(
            model="test-model",
            messages=[{"role": "user", "content": "test prompt"}],
            stream=True,
        )

    @pytest.mark.asyncio
    async def test_gen_stream_handles_empty_content(self, mock_ollama_client_instance):
        """Test that streaming handles chunks with no content"""

        async def mock_stream_with_empty():
            yield {"message": {"content": "First"}}
            yield {"message": {"content": ""}}  # Empty content
            yield {"message": {"content": "Last"}}

        client = OllamaLocalClient()
        mock_ollama_client_instance.chat.return_value = mock_stream_with_empty()

        chunks = [chunk async for chunk in client.gen_stream("prompt", "model")]
        assert chunks == ["First", "Last"]
