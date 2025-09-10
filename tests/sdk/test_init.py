import os
from unittest.mock import patch

import pytest


@pytest.mark.skip(reason="create_client factory not found, tests are outdated")
class TestCreateClientFactory:
    """Test cases for the create_client factory function"""

    @patch.dict(
        os.environ,
        {"OLM_CLIENT_MODE": "local"},
        clear=True,
    )
    def test_create_client_local_mode(self):
        """Test that create_client returns OllamaLocalClient in local mode"""
        from sdk.olm_api_client import create_client
        from sdk.olm_api_client.local_client import OllamaLocalClient

        client = create_client()
        assert isinstance(client, OllamaLocalClient)

    @patch.dict(
        os.environ,
        {"OLM_CLIENT_MODE": "remote", "OLM_API_ENDPOINT": "http://remote:8000"},
        clear=True,
    )
    def test_create_client_remote_mode(self):
        """Test that create_client returns OllamaApiClient in remote mode"""
        from sdk.olm_api_client import create_client
        from sdk.olm_api_client.client import OllamaApiClient

        client = create_client()
        assert isinstance(client, OllamaApiClient)
        assert client.api_url == "http://remote:8000"

    @patch.dict(os.environ, {}, clear=True)
    def test_create_client_remote_mode_default(self):
        """Test that create_client defaults to remote mode"""
        from sdk.olm_api_client import create_client
        from sdk.olm_api_client.client import OllamaApiClient

        with patch.dict(os.environ, {"OLM_API_ENDPOINT": "http://default:8000"}):
            client = create_client()
            assert isinstance(client, OllamaApiClient)

    @patch.dict(os.environ, {"OLM_CLIENT_MODE": "remote"}, clear=True)
    def test_create_client_remote_mode_raises_error_if_no_endpoint(self):
        """Test that remote mode raises ValueError if OLM_API_ENDPOINT is not set"""
        from sdk.olm_api_client import create_client

        with pytest.raises(
            ValueError, match="OLM_API_ENDPOINT must be set for 'remote' client mode"
        ):
            create_client()

    @patch.dict(os.environ, {"OLM_CLIENT_MODE": "mock"}, clear=True)
    def test_create_client_mock_mode(self):
        """Test that create_client returns MockOllamaApiClient in mock mode"""
        from sdk.olm_api_client import create_client
        from sdk.olm_api_client.mock import MockOllamaApiClient

        client = create_client()
        assert isinstance(client, MockOllamaApiClient)

    @patch.dict(os.environ, {"OLM_CLIENT_MODE": "invalid_mode"}, clear=True)
    def test_create_client_invalid_mode_raises_error(self):
        """Test that an invalid mode raises a ValueError"""
        from sdk.olm_api_client import create_client

        with pytest.raises(ValueError, match="Invalid OLM_CLIENT_MODE"):
            create_client()
