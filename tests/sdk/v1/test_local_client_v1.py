from unittest.mock import AsyncMock, patch

import pytest

from sdk.olm_api_client.v1.local_client import OlmLocalClientV1
from sdk.olm_api_client.v1.protocol import OlmClientV1Protocol


@pytest.fixture
def mock_ollama_client_instance():
    """
    Fixture that patches `ollama.AsyncClient` and yields a mock instance.
    This prevents the actual client from being created while allowing tests
    to configure the behavior of the instance's methods.
    """
    with patch("sdk.olm_api_client.v1.local_client.ollama.AsyncClient") as mock_class:
        mock_instance = AsyncMock()
        mock_class.return_value = mock_instance
        yield mock_instance


class TestOlmLocalClientV1:
    """Test cases for OlmLocalClientV1"""

    def test_implements_protocol(self):
        """Test that OlmLocalClientV1 implements OlmClientV1Protocol"""
        client = OlmLocalClientV1()
        assert isinstance(client, OlmClientV1Protocol)

    @pytest.mark.asyncio
    async def test_generate_batch_success(self, mock_ollama_client_instance):
        """Test successful batch generation"""
        client = OlmLocalClientV1()
        mock_ollama_client_instance.chat.return_value = {
            "message": {"content": "Test response"}
        }

        response = await client.generate("test prompt", "test-model", stream=False)
        assert response == "Test response"
        mock_ollama_client_instance.chat.assert_called_once_with(
            model="test-model",
            messages=[{"role": "user", "content": "test prompt"}],
            stream=False,
            options={},
        )

    @pytest.mark.asyncio
    async def test_generate_stream_success(self, mock_ollama_client_instance):
        """Test successful stream generation"""

        async def mock_stream():
            yield {"message": {"content": "Hello"}}
            yield {"message": {"content": " "}}
            yield {"message": {"content": "World"}}

        client = OlmLocalClientV1()
        mock_ollama_client_instance.chat.return_value = mock_stream()

        result = await client.generate("test prompt", "test-model", stream=True)
        chunks = [chunk async for chunk in result]
        assert "".join(chunks) == "Hello World"
        mock_ollama_client_instance.chat.assert_called_once_with(
            model="test-model",
            messages=[{"role": "user", "content": "test prompt"}],
            stream=True,
            options={},
        )

    @pytest.mark.asyncio
    async def test_generate_handles_empty_content(self, mock_ollama_client_instance):
        """Test that streaming handles chunks with no content"""

        async def mock_stream_with_empty():
            yield {"message": {"content": "First"}}
            yield {"message": {"content": ""}}  # Empty content
            yield {"message": {"content": "Last"}}

        client = OlmLocalClientV1()
        mock_ollama_client_instance.chat.return_value = mock_stream_with_empty()

        result = await client.generate("prompt", "model", stream=True)
        chunks = [chunk async for chunk in result]
        assert chunks == ["First", "Last"]
