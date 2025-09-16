from unittest.mock import MagicMock, patch

import httpx
import pytest
from olm_api_sdk.v1.client import OlmApiClientV1
from olm_api_sdk.v1.protocol import OlmClientV1Protocol


class TestOlmApiClientV1Sync:
    """Test cases for OlmApiClientV1 synchronous methods"""

    def test_init_success(self):
        """Test successful initialization with API URL"""
        api_url = "http://localhost:11434"
        client = OlmApiClientV1(api_url=api_url)
        assert client.api_url == api_url
        assert client.generate_endpoint == f"{api_url}/api/v1/chat"

    def test_implements_protocol(self):
        """Test that OlmApiClientV1 implements OlmClientV1Protocol"""
        client = OlmApiClientV1(api_url="http://localhost:11434")
        assert isinstance(client, OlmClientV1Protocol)

    def test_build_payload_helper(self):
        """Test _build_payload helper method"""
        client = OlmApiClientV1(api_url="http://localhost:11434")

        # Test with minimal parameters
        payload = client._build_payload("test prompt", "test-model")
        assert payload["prompt"] == "test prompt"
        assert payload["model_name"] == "test-model"
        assert payload["stream"] is False
        assert "think" not in payload

        # Test with all parameters
        payload = client._build_payload(
            "test prompt", "test-model", stream=True, think=True
        )
        assert payload["prompt"] == "test prompt"
        assert payload["model_name"] == "test-model"
        assert payload["stream"] is True
        assert payload["think"] is True

    def test_generate_sync_success(self):
        """Test successful synchronous generate"""
        client = OlmApiClientV1(api_url="http://localhost:11434")

        mock_response = {
            "think": "some thinking",
            "content": "Complete response",
            "response": "Complete response",
        }

        with patch.object(client, "_non_stream_response_sync") as mock_sync:
            mock_sync.return_value = mock_response

            result = client.generate_sync("test prompt", "test-model")

            assert result == mock_response
            assert "think" in result
            assert "content" in result
            assert "response" in result
            mock_sync.assert_called_once_with("test prompt", "test-model", None)

    def test_generate_sync_with_think(self):
        """Test synchronous generate with think parameter"""
        client = OlmApiClientV1(api_url="http://localhost:11434")

        mock_response = {
            "think": "detailed thinking process",
            "content": "Response with thinking",
            "response": "Response with thinking",
        }

        with patch.object(client, "_non_stream_response_sync") as mock_sync:
            mock_sync.return_value = mock_response

            result = client.generate_sync("test prompt", "test-model", think=True)

            assert result == mock_response
            mock_sync.assert_called_once_with("test prompt", "test-model", True)


class TestOlmApiClientV1SyncIntegration:
    """Integration tests for synchronous methods using httpx mocking"""

    def test_non_stream_response_sync_success(self):
        """Test successful synchronous non-streaming response"""
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
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response

        # Create mock sync client context
        mock_sync_client = MagicMock()
        mock_sync_client.__enter__.return_value = mock_client
        mock_sync_client.__exit__.return_value = None

        with patch("httpx.Client", return_value=mock_sync_client):
            result = client._non_stream_response_sync("test prompt", "test-model")

            assert isinstance(result, dict)
            assert "think" in result
            assert "content" in result
            assert "response" in result
            assert result["content"] == "Complete response text"
            mock_client.post.assert_called_once()

            # Verify the post call was made with correct parameters
            call_args = mock_client.post.call_args
            assert call_args[1]["json"]["prompt"] == "test prompt"
            assert call_args[1]["json"]["model_name"] == "test-model"
            assert call_args[1]["json"]["stream"] is False

    def test_non_stream_response_sync_with_think(self):
        """Test synchronous response with think parameter"""
        client = OlmApiClientV1(api_url="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "think": "detailed thinking process",
            "content": "Response with thinking",
            "response": "Response with thinking",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response

        mock_sync_client = MagicMock()
        mock_sync_client.__enter__.return_value = mock_client
        mock_sync_client.__exit__.return_value = None

        with patch("httpx.Client", return_value=mock_sync_client):
            result = client._non_stream_response_sync(
                "test prompt", "test-model", think=True
            )

            assert result["think"] == "detailed thinking process"

            # Verify the payload includes think parameter
            call_args = mock_client.post.call_args
            assert call_args[1]["json"]["think"] is True

    def test_non_stream_response_sync_handles_request_error(self):
        """Test that synchronous method handles httpx.RequestError"""
        client = OlmApiClientV1(api_url="http://localhost:11434")

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.post.side_effect = httpx.RequestError("Connection failed")

            with pytest.raises(httpx.RequestError):
                client._non_stream_response_sync("test prompt", "test-model")

    def test_non_stream_response_sync_handles_http_status_error(self):
        """Test that synchronous method handles HTTP status errors"""
        client = OlmApiClientV1(api_url="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error", request=MagicMock(), response=MagicMock()
        )

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response

        mock_sync_client = MagicMock()
        mock_sync_client.__enter__.return_value = mock_client
        mock_sync_client.__exit__.return_value = None

        with patch("httpx.Client", return_value=mock_sync_client):
            with pytest.raises(httpx.HTTPStatusError):
                client._non_stream_response_sync("test prompt", "test-model")

    def test_generate_sync_integration(self):
        """Test full integration of generate_sync method"""
        client = OlmApiClientV1(api_url="http://localhost:11434")

        expected_response = {
            "think": "integration test thinking",
            "content": "Integration test response",
            "response": "Integration test response",
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
            result = client.generate_sync("integration test", "test-model", think=True)

            assert result == expected_response
            assert result["content"] == "Integration test response"

            # Verify correct endpoint and payload
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "http://localhost:11434/api/v1/chat"
            assert call_args[1]["json"]["prompt"] == "integration test"
            assert call_args[1]["json"]["model_name"] == "test-model"
            assert call_args[1]["json"]["think"] is True
            assert call_args[1]["json"]["stream"] is False
