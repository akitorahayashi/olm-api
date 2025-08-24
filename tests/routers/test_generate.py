from unittest.mock import MagicMock

import httpx
import pytest
from httpx import AsyncClient
from starlette import status

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
    # Mock the context manager
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_session
    mock_context_manager.__exit__.return_value = None
    monkeypatch.setattr(
        "src.dependencies.logging.create_db_session",
        lambda: mock_context_manager,
    )
    return mock_session


async def test_generate_uses_active_model(
    client: AsyncClient, mock_ollama_client: MagicMock
):
    """
    Test that the /generate endpoint uses the model set in app_state.
    """
    # Arrange
    active_model = "my-active-model:latest"
    app_state.set_current_model(active_model)
    mock_ollama_client.chat.return_value = {"message": {"content": "response"}}

    # Act
    response = await client.post(
        "/api/v1/generate", json={"prompt": "Test prompt", "stream": False}
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    mock_ollama_client.chat.assert_called_once()
    assert mock_ollama_client.chat.call_args.kwargs["model"] == active_model


async def test_generate_success_logs_metadata(
    client: AsyncClient,
    mock_ollama_client: MagicMock,
    mock_db_session_fixture: MagicMock,
):
    """Test that a successful request logs basic metadata."""
    mock_ollama_client.chat.return_value = {"message": {"content": "response"}}
    response = await client.post(
        "/api/v1/generate", json={"prompt": "Hello", "stream": False}
    )

    assert response.status_code == 200
    mock_db_session_fixture.add.assert_called_once()
    log_entry = mock_db_session_fixture.add.call_args[0][0]
    assert isinstance(log_entry, Log)
    assert log_entry.response_status_code == 200


async def test_generate_api_error_logs_details(
    client: AsyncClient,
    mock_ollama_client: MagicMock,
    mock_db_session_fixture: MagicMock,
):
    """
    Test that a service-layer error from Ollama is handled by the global
    exception handler and that the error details are logged correctly.
    """
    # Arrange: Mock the service to raise an exception that the global handler will catch
    mock_ollama_client.chat.side_effect = httpx.RequestError(
        "Ollama go boom", request=MagicMock(url="http://test.url/api")
    )

    # Act: Make the request
    response = await client.post(
        "/api/v1/generate", json={"prompt": "Cause an error", "stream": False}
    )

    # Assert: Check that the global handler returned the correct status code
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert "Error connecting to upstream service" in response.json()["detail"]

    # Assert: Check that the logging middleware still recorded the request
    mock_db_session_fixture.add.assert_called_once()
    log_entry = mock_db_session_fixture.add.call_args[0][0]
    assert isinstance(log_entry, Log)
    # The status code logged should be the one returned to the client
    assert log_entry.response_status_code == status.HTTP_502_BAD_GATEWAY
    assert log_entry.error_details is not None
    assert "httpx.RequestError" in log_entry.error_details
