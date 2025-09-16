from unittest.mock import MagicMock, patch

import httpx
import pytest
from olm_api_sdk.v2.client import OlmApiClientV2
from olm_api_sdk.v2.protocol import OlmClientV2Protocol


class TestOlmApiClientV2Sync:
    """Test cases for OlmApiClientV2 synchronous methods"""

    def test_init_success(self):
        """Test successful initialization with API URL"""
        api_url = "http://localhost:8000"
        client = OlmApiClientV2(api_url)

        assert client.api_url == api_url
        assert client.chat_endpoint == f"{api_url}/api/v2/chat"

    def test_implements_protocol(self):
        """Test that OlmApiClientV2 implements OlmClientV2Protocol"""
        client = OlmApiClientV2(api_url="http://localhost:8000")
        assert isinstance(client, OlmClientV2Protocol)

    def test_build_payload_helper(self):
        """Test _build_payload helper method"""
        client = OlmApiClientV2(api_url="http://localhost:8000")

        messages = [{"role": "user", "content": "test message"}]

        # Test with minimal parameters
        payload = client._build_payload(messages, "test-model")
        assert payload["messages"] == messages
        assert payload["model"] == "test-model"
        assert payload["stream"] is False
        assert "tools" not in payload

        # Test with all parameters
        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        payload = client._build_payload(
            messages, "test-model", tools=tools, stream=True, temperature=0.7
        )
        assert payload["messages"] == messages
        assert payload["model"] == "test-model"
        assert payload["stream"] is True
        assert payload["tools"] == tools
        assert payload["temperature"] == 0.7

    def test_generate_sync_success(self):
        """Test successful synchronous generate"""
        client = OlmApiClientV2(api_url="http://localhost:8000")

        mock_response = {"choices": [{"message": {"content": "Complete response"}}]}

        with patch.object(client, "_chat_non_stream_response_sync") as mock_sync:
            mock_sync.return_value = mock_response

            messages = [{"role": "user", "content": "test prompt"}]
            result = client.generate_sync(messages, "test-model")

            assert result == mock_response
            assert "choices" in result
            mock_sync.assert_called_once()

    def test_generate_sync_with_tools(self):
        """Test synchronous generate with tools parameter"""
        client = OlmApiClientV2(api_url="http://localhost:8000")

        mock_response = {
            "choices": [
                {"message": {"tool_calls": [{"function": {"name": "save_thought"}}]}}
            ]
        }

        with patch.object(client, "_chat_non_stream_response_sync") as mock_sync:
            mock_sync.return_value = mock_response

            messages = [{"role": "user", "content": "test prompt"}]
            tools = [{"type": "function", "function": {"name": "save_thought"}}]
            result = client.generate_sync(messages, "test-model", tools=tools)

            assert result == mock_response
            mock_sync.assert_called_once()

    def test_generate_sync_with_generation_parameters(self):
        """Test synchronous generate with additional parameters"""
        client = OlmApiClientV2(api_url="http://localhost:8000")

        mock_response = {
            "choices": [{"message": {"content": "Response with custom parameters"}}]
        }

        with patch.object(client, "_chat_non_stream_response_sync") as mock_sync:
            mock_sync.return_value = mock_response

            messages = [{"role": "user", "content": "test prompt"}]
            result = client.generate_sync(
                messages, "test-model", temperature=0.7, top_p=0.9, max_tokens=100
            )

            assert result == mock_response
            mock_sync.assert_called_once()


class TestOlmApiClientV2SyncIntegration:
    """Integration tests for synchronous methods using httpx mocking"""

    def test_chat_non_stream_response_sync_success(self):
        """Test successful synchronous non-streaming response"""
        client = OlmApiClientV2(api_url="http://localhost:8000")

        # Create mock response object
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Complete response text"}}]
        }
        mock_response.raise_for_status = MagicMock()

        # Create mock client
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response

        # Create mock sync client context
        mock_sync_client = MagicMock()
        mock_sync_client.__enter__.return_value = mock_client
        mock_sync_client.__exit__.return_value = None

        payload = {"model": "test-model", "messages": [], "stream": False}

        with patch("httpx.Client", return_value=mock_sync_client):
            result = client._chat_non_stream_response_sync(payload)

            assert isinstance(result, dict)
            assert "choices" in result
            assert (
                result["choices"][0]["message"]["content"] == "Complete response text"
            )
            mock_client.post.assert_called_once()

            # Verify the post call was made with correct parameters
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "http://localhost:8000/api/v2/chat"
            assert call_args[1]["json"] == payload
            assert call_args[1]["headers"]["Accept"] == "application/json"

    def test_chat_non_stream_response_sync_with_tools(self):
        """Test synchronous response with tools"""
        client = OlmApiClientV2(api_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"tool_calls": [{"function": {"name": "save_thought"}}]}}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response

        mock_sync_client = MagicMock()
        mock_sync_client.__enter__.return_value = mock_client
        mock_sync_client.__exit__.return_value = None

        payload = {
            "model": "test-model",
            "messages": [],
            "tools": [{"type": "function", "function": {"name": "save_thought"}}],
            "stream": False,
        }

        with patch("httpx.Client", return_value=mock_sync_client):
            result = client._chat_non_stream_response_sync(payload)

            assert "choices" in result
            assert "tool_calls" in result["choices"][0]["message"]

            # Verify the payload includes tools
            call_args = mock_client.post.call_args
            assert "tools" in call_args[1]["json"]

    def test_chat_non_stream_response_sync_handles_request_error(self):
        """Test that synchronous method handles httpx.RequestError"""
        client = OlmApiClientV2(api_url="http://localhost:8000")

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.post.side_effect = httpx.RequestError("Connection failed")

            payload = {"model": "test-model", "messages": [], "stream": False}

            with pytest.raises(httpx.RequestError):
                client._chat_non_stream_response_sync(payload)

    def test_chat_non_stream_response_sync_handles_http_status_error(self):
        """Test that synchronous method handles HTTP status errors"""
        client = OlmApiClientV2(api_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error", request=MagicMock(), response=MagicMock()
        )

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response

        mock_sync_client = MagicMock()
        mock_sync_client.__enter__.return_value = mock_client
        mock_sync_client.__exit__.return_value = None

        payload = {"model": "test-model", "messages": [], "stream": False}

        with patch("httpx.Client", return_value=mock_sync_client):
            with pytest.raises(httpx.HTTPStatusError):
                client._chat_non_stream_response_sync(payload)

    def test_generate_sync_integration(self):
        """Test full integration of generate_sync method"""
        client = OlmApiClientV2(api_url="http://localhost:8000")

        expected_response = {
            "choices": [{"message": {"content": "Integration test response"}}]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response

        mock_sync_client = MagicMock()
        mock_sync_client.__enter__.return_value = mock_client
        mock_sync_client.__exit__.return_value = None

        with patch("httpx.Client", return_value=mock_sync_client):
            messages = [{"role": "user", "content": "integration test"}]
            tools = [{"type": "function", "function": {"name": "test_tool"}}]
            result = client.generate_sync(
                messages, "test-model", tools=tools, temperature=0.8
            )

            assert result == expected_response
            assert (
                result["choices"][0]["message"]["content"]
                == "Integration test response"
            )

            # Verify correct endpoint and payload structure
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "http://localhost:8000/api/v2/chat"
            payload = call_args[1]["json"]
            assert payload["messages"] == messages
            assert payload["model"] == "test-model"
            assert payload["tools"] == tools
            assert payload["temperature"] == 0.8
            assert payload["stream"] is False
