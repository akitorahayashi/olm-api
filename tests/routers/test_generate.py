from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from src.dependencies.common import get_ollama_client
from src.main import app
from src.models.log import Log

# --- Mock Setup ---
mock_ollama_client = MagicMock()


def override_get_ollama_client():
    return mock_ollama_client


# --- Fixtures ---


@pytest.fixture
def override_ollama_client_dep():
    app.dependency_overrides[get_ollama_client] = override_get_ollama_client
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_ollama_client, None)


@pytest.fixture(autouse=True)
def mock_db_session(monkeypatch):
    mock_session = MagicMock()
    monkeypatch.setattr(
        "src.dependencies.logging.create_db_session", lambda: mock_session
    )
    return mock_session


@pytest.fixture
def client(mock_db_session, override_ollama_client_dep):
    mock_ollama_client.reset_mock(return_value=True, side_effect=None)
    mock_ollama_client.chat = MagicMock()
    with TestClient(app) as test_client:
        yield test_client


# --- Test Cases ---


def test_generate_success_logs_metadata(client, mock_db_session):
    """Test that a successful request logs basic metadata."""
    mock_chat_response = {"message": {"content": "Mocked response"}}
    mock_ollama_client.chat.return_value = mock_chat_response

    response = client.post(
        "/api/v1/generate", json={"prompt": "Hello", "stream": False}
    )

    assert response.status_code == 200
    mock_db_session.add.assert_called_once()
    log_entry = mock_db_session.add.call_args[0][0]
    assert isinstance(log_entry, Log)
    assert log_entry.response_status_code == 200
    assert log_entry.error_details is None
    assert log_entry.prompt == "[Not Logged]"
    assert log_entry.generated_response == "[Not Logged]"


def test_generate_stream_success_logs_metadata(client, mock_db_session):
    """Test that a successful streaming request logs basic metadata."""
    mock_stream_data = [{"message": {"content": "Stream"}}]
    mock_ollama_client.chat.return_value = iter(mock_stream_data)

    response = client.post(
        "/api/v1/generate", json={"prompt": "Stream this", "stream": True}
    )

    assert response.status_code == 200
    mock_db_session.add.assert_called_once()
    log_entry = mock_db_session.add.call_args[0][0]
    assert isinstance(log_entry, Log)
    assert log_entry.response_status_code == 200
    assert log_entry.error_details is None


def test_generate_api_error_logs_details(client, mock_db_session):
    """Test that an API error logs detailed exception info."""
    mock_ollama_client.chat.side_effect = httpx.RequestError(
        "Ollama go boom", request=MagicMock()
    )

    with pytest.raises(httpx.RequestError):
        client.post(
            "/api/v1/generate", json={"prompt": "Cause an error", "stream": False}
        )
    mock_db_session.add.assert_called_once()
    log_entry = mock_db_session.add.call_args[0][0]
    assert isinstance(log_entry, Log)
    assert log_entry.response_status_code == 500
    assert log_entry.error_details is not None
    assert "httpx.RequestError" in log_entry.error_details
