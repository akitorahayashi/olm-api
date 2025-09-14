from unittest.mock import patch

import pytest

from sdk.olm_api_client.v2.client import OlmApiClientV2
from sdk.olm_api_client.v2.protocol import OlmClientV2Protocol


class TestOlmApiClientV2:
    """Test cases for OlmApiClientV2"""

    def test_init_success(self):
        """Test successful initialization with API URL"""
        api_url = "http://localhost:8000"
        client = OlmApiClientV2(api_url)

        assert client.api_url == api_url
        assert client.chat_endpoint == f"{api_url}/api/v2/chat/completions"

    def test_init_without_api_url_raises_error(self):
        """Test initialization without required api_url raises TypeError"""
        with pytest.raises(TypeError):
            OlmApiClientV2()

    def test_implements_protocol(self):
        """Test that OlmApiClientV2 implements OlmClientV2Protocol"""
        client = OlmApiClientV2(api_url="http://localhost:8000")
        assert isinstance(client, OlmClientV2Protocol)

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from API URL"""
        api_url = "http://localhost:8000/"
        client = OlmApiClientV2(api_url)

        assert client.api_url == "http://localhost:8000"
        assert client.chat_endpoint == "http://localhost:8000/api/v2/chat/completions"

    @pytest.mark.asyncio
    async def test_generate_streaming(self):
        """Test generate method with streaming returns JSON objects"""
        client = OlmApiClientV2(api_url="http://localhost:11434")

        with patch.object(client, "_chat_stream_response") as mock_stream:
            mock_stream.return_value = async_generator_mock(
                [
                    {"choices": [{"delta": {"content": "Hello"}}]},
                    {"choices": [{"delta": {"content": " world"}}]},
                ]
            )

            messages = [{"role": "user", "content": "test prompt"}]
            result = await client.generate(messages, "test-model", stream=True)

            # Collect and verify JSON objects are returned
            chunks = []
            async for chunk in result:
                chunks.append(chunk)

            assert len(chunks) == 2
            assert chunks[0]["choices"][0]["delta"]["content"] == "Hello"
            assert chunks[1]["choices"][0]["delta"]["content"] == " world"

    @pytest.mark.asyncio
    async def test_generate_non_streaming(self):
        """Test generate method without streaming"""
        client = OlmApiClientV2(api_url="http://localhost:11434")

        with patch.object(client, "_chat_non_stream_response") as mock_non_stream:
            expected_response = {
                "choices": [{"message": {"content": "Complete response"}}]
            }
            mock_non_stream.return_value = expected_response

            messages = [{"role": "user", "content": "test prompt"}]
            result = await client.generate(messages, "test-model", stream=False)

            assert result == expected_response
            mock_non_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_tools(self):
        """Test generate method with tools"""
        client = OlmApiClientV2(api_url="http://localhost:11434")

        with patch.object(client, "_chat_non_stream_response") as mock_non_stream:
            expected_response = {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [{"function": {"name": "save_thought"}}]
                        }
                    }
                ]
            }
            mock_non_stream.return_value = expected_response

            messages = [{"role": "user", "content": "test prompt"}]
            tools = [{"type": "function", "function": {"name": "save_thought"}}]
            result = await client.generate(
                messages, "test-model", tools=tools, stream=False
            )

            assert result == expected_response
            mock_non_stream.assert_called_once()


def async_generator_mock(data_list):
    """Helper to create async generator mock"""

    async def _generator():
        for item in data_list:
            yield item

    return _generator()
