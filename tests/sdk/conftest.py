import pytest

from sdk.olm_api_client.mock import MockOllamaApiClient


@pytest.fixture
def mock_client():
    """
    Provides a MockOllamaApiClient with zero delay and predictable responses for fast testing.
    """
    predictable_responses = [
        "Test response 1",
        "Test response 2",
        "Test response 3",
        "Test response 4",
        "Test response 5",
    ]
    return MockOllamaApiClient(token_delay=0, responses=predictable_responses)


@pytest.fixture
def slow_mock_client():
    """
    Provides a MockOllamaApiClient with realistic delay and predictable responses for testing streaming behavior.
    """
    predictable_responses = [
        "Slow test response 1",
        "Slow test response 2",
        "Slow test response 3",
    ]
    return MockOllamaApiClient(token_delay=0.01, responses=predictable_responses)


@pytest.fixture
def custom_response_client():
    """
    Provides a MockOllamaApiClient with custom responses for specific test scenarios.
    """

    def _create_client(responses):
        return MockOllamaApiClient(token_delay=0, responses=responses)

    return _create_client
