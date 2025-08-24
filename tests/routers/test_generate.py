from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.config.state import app_state
from src.models.log import Log

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def mock_db_session_fixture(monkeypatch):
    """
    Mock the DB session for the logging middleware for all tests in this file.
    """
    mock_session = MagicMock()
    monkeypatch.setattr(
        "src.dependencies.logging.create_db_session", lambda: mock_session
    )
    return mock_session


async def test_generate_uses_active_model(
    client: TestClient, mock_ollama_client: MagicMock
):
    """
    Test that the /generate endpoint uses the model set in app_state.
    """
    # Arrange
    active_model = "my-active-model:latest"
    app_state.set_current_model(active_model)
    mock_ollama_client.chat.return_value = {"message": {"content": "response"}}

    # Act
    response = client.post(
        "/api/v1/generate", json={"prompt": "Test prompt", "stream": False}
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    mock_ollama_client.chat.assert_called_once()
    assert mock_ollama_client.chat.call_args.kwargs["model"] == active_model


async def test_generate_success_logs_metadata(
    client: TestClient,
    mock_ollama_client: MagicMock,
    mock_db_session_fixture: MagicMock,
):
    """Test that a successful request logs basic metadata."""
    mock_ollama_client.chat.return_value = {"message": {"content": "response"}}
    response = client.post(
        "/api/v1/generate", json={"prompt": "Hello", "stream": False}
    )

    assert response.status_code == 200
    mock_db_session_fixture.add.assert_called_once()
    log_entry = mock_db_session_fixture.add.call_args[0][0]
    assert isinstance(log_entry, Log)
    assert log_entry.response_status_code == 200


async def test_generate_api_error_logs_details(
    client: TestClient,
    mock_ollama_client: MagicMock,
    mock_db_session_fixture: MagicMock,
):
    """Test that a service-layer error from Ollama is handled and logged."""
    mock_ollama_client.chat.side_effect = httpx.RequestError(
        "Ollama go boom", request=MagicMock()
    )

    with pytest.raises(httpx.RequestError):
        client.post(
            "/api/v1/generate", json={"prompt": "Cause an error", "stream": False}
        )

    mock_db_session_fixture.add.assert_called_once()
    log_entry = mock_db_session_fixture.add.call_args[0][0]
    assert isinstance(log_entry, Log)
    assert log_entry.response_status_code == 500
    assert log_entry.error_details is not None
    assert "httpx.RequestError" in log_entry.error_details
