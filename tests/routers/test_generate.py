from unittest.mock import MagicMock

import ollama
import pytest
from fastapi.testclient import TestClient

from src.dependencies.common import get_ollama_client
from src.main import app

# --- Mock Setup ---
# Mock the ollama client to avoid actual API calls
mock_ollama_client = MagicMock()


def override_get_ollama_client():
    """Override dependency to return a mock ollama client."""
    return mock_ollama_client


# Apply the dependency override to the app
app.dependency_overrides[get_ollama_client] = override_get_ollama_client


# --- Fixtures ---


@pytest.fixture(autouse=True)
def mock_db_session(monkeypatch):
    """Mock the database session for all tests to prevent actual DB calls."""
    mock_session = MagicMock()
    # The middleware now calls get_db_session, so we patch that function
    mock_get_session = MagicMock(return_value=mock_session)
    monkeypatch.setattr("src.dependencies.logging.get_db_session", mock_get_session)
    return mock_session


@pytest.fixture
def client(mock_db_session):
    """Fixture to create a TestClient for the app."""
    # Reset the mock's state before each test
    mock_ollama_client.reset_mock()
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
    """Test the /api/v1/generate endpoint for a successful streaming response."""

    mock_stream_data = [
        {"message": {"content": "Stream "}},
        {"message": {"content": "response"}},
    ]
    mock_ollama_client.chat.return_value = iter(mock_stream_data)

    response = client.post(
        "/api/v1/generate", json={"prompt": "Stream this", "stream": True}
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    full_response = "".join(response.iter_text())
    assert full_response == "Stream response"
    mock_ollama_client.chat.assert_called_once_with(
        model="test-model",
        messages=[{"role": "user", "content": "Stream this"}],
        stream=True,
    )


def test_generate_ollama_api_error(client):
    """Test the /api/v1/generate endpoint when the Ollama API returns an error."""
    error_message = "Ollama server is not available"
    mock_ollama_client.chat.side_effect = ollama.ResponseError(
        error_message, status_code=503
    )

    response = client.post(
        "/api/v1/generate", json={"prompt": "Cause an error", "stream": False}
    )

    assert response.status_code == 500
    assert response.json() == {"detail": f"Ollama API error: {error_message}"}
    mock_ollama_client.chat.assert_called_once()
