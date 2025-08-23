from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from src.services.ollama import get_ollama_client
from src.main import app

# --- Mock Setup ---
# This will be used by the override fixture
mock_ollama_client = MagicMock()


def override_get_ollama_client():
    """Override dependency to return the shared mock ollama client."""
    return mock_ollama_client


# --- Fixtures ---


@pytest.fixture
def override_ollama_client_dep():
    """Fixture to safely override and restore the ollama client dependency."""
    app.dependency_overrides[get_ollama_client] = override_get_ollama_client
    try:
        yield
    finally:
        # Clean up the override after the test to ensure test isolation
        app.dependency_overrides.pop(get_ollama_client, None)


@pytest.fixture(autouse=True)
def mock_db_session(monkeypatch):
    """Mock the database session creation to prevent actual DB calls."""
    mock_session = MagicMock()
    # The middleware calls create_db_session directly, so we patch that
    monkeypatch.setattr(
        "src.dependencies.logging.create_db_session", lambda: mock_session
    )
    return mock_session


@pytest.fixture
def client(mock_db_session, override_ollama_client_dep):
    """Fixture to create a TestClient for the app."""
    # Fully reset the mock's state, including return_value and side_effect
    mock_ollama_client.reset_mock(return_value=True, side_effect=None)
    # Re-create the 'chat' attribute to ensure it's clean
    mock_ollama_client.chat = MagicMock()

    with TestClient(app) as test_client:
        yield test_client


# --- Test Cases ---


def test_generate_success(client):
    """Test the /api/v1/generate endpoint for a successful non-streaming response."""
    mock_chat_response = {"message": {"content": "Mocked response"}}
    mock_ollama_client.chat.return_value = mock_chat_response

    response = client.post(
        "/api/v1/generate", json={"prompt": "Hello", "stream": False}
    )

    assert response.status_code == 200
    assert response.json() == {"response": "Mocked response"}
    mock_ollama_client.chat.assert_called_once_with(
        model="test-model",
        messages=[{"role": "user", "content": "Hello"}],
        stream=False,
    )


def test_generate_stream_success(client):
    """Test the /api/v1/generate endpoint for a successful SSE streaming response."""
    mock_stream_data = [
        {"message": {"content": "Stream"}},
        {"message": {"content": " Response"}},
    ]
    mock_ollama_client.chat.return_value = iter(mock_stream_data)

    response = client.post(
        "/api/v1/generate", json={"prompt": "Stream this", "stream": True}
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    # The response text should now be in Server-Sent Events format
    assert response.text == "data: Stream\n\ndata:  Response\n\n"
    mock_ollama_client.chat.assert_called_once_with(
        model="test-model",
        messages=[{"role": "user", "content": "Stream this"}],
        stream=True,
    )


def test_generate_ollama_api_error(client):
    """Test the /api/v1/generate endpoint when the Ollama API returns an error."""
    error_message = "Ollama server is not available"
    # Use an exception type that the application code now handles
    mock_ollama_client.chat.side_effect = httpx.RequestError(
        error_message, request=MagicMock()
    )

    response = client.post(
        "/api/v1/generate", json={"prompt": "Cause an error", "stream": False}
    )

    assert response.status_code == 500
    # The error message is now more generic and safer
    assert response.json() == {
        "detail": "Ollama API error: Could not connect to the service."
    }
    mock_ollama_client.chat.assert_called_once()
