import pytest

from sdk.olm_api_client.mock import MockOllamaApiClient


@pytest.fixture
def mock_client():
    """
    Provides a MockOllamaApiClient with zero delay for fast testing.
    """
    return MockOllamaApiClient(token_delay=0)


@pytest.fixture
def slow_mock_client():
    """
    Provides a MockOllamaApiClient with realistic delay for testing streaming behavior.
    """
    return MockOllamaApiClient(token_delay=0.01)
