import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.dependencies.common import get_ollama_client
from src.main import app


@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """
    Set environment variables required for the tests.
    This runs once per test session.
    """
    os.environ["BUILT_IN_OLLAMA_MODEL"] = "test-built-in-model"
    os.environ["DEFAULT_GENERATION_MODEL"] = "test-default-model"
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"


@pytest.fixture
def mock_ollama_client():
    """
    Fixture to mock the Ollama client using FastAPI's dependency overrides.
    This ensures that any call to the get_ollama_client dependency returns a mock
    instead of a real client.
    """
    mock_client = MagicMock()
    # The actual ollama client methods are synchronous, so the mock methods
    # should be regular MagicMocks, not AsyncMocks. The service layer handles
    # running them in a threadpool.
    mock_client.chat = MagicMock()
    mock_client.list = MagicMock()
    mock_client.pull = MagicMock()
    mock_client.delete = MagicMock()

    # This is the override function that will be called by FastAPI
    def override_get_ollama_client():
        return mock_client

    # Apply the override
    app.dependency_overrides[get_ollama_client] = override_get_ollama_client

    yield mock_client  # The test will receive this mock instance

    # Clean up the override after the test is done
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def client():
    """
    Create a TestClient instance for the entire test module.
    """
    with TestClient(app) as c:
        yield c
