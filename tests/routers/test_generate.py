from unittest.mock import MagicMock

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from starlette import status

from src.config.app_state import app_state
from src.db.models.log import Log

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_generate_uses_active_model(
    client: AsyncClient, mock_ollama_service: MagicMock, db_session: Session
):
    """
    Test that the /generate endpoint uses the model set in app_state.
    """
    active_model = "my-active-model:latest"
    app_state.set_current_model(active_model)
    mock_ollama_service.generate_response.return_value = {
        "message": {"content": "response"}
    }

    response = await client.post(
        "/api/v1/generate", json={"prompt": "Test prompt", "stream": False}
    )

    assert response.status_code == status.HTTP_200_OK
    mock_ollama_service.generate_response.assert_called_once()
    assert (
        mock_ollama_service.generate_response.call_args.kwargs["model_name"]
        == active_model
    )


async def test_generate_success_logs_metadata(
    client: AsyncClient,
    mock_ollama_service: MagicMock,
    db_session: Session,
):
    """Test that a successful request logs basic metadata."""
    mock_ollama_service.generate_response.return_value = {
        "message": {"content": "response"}
    }
    response = await client.post(
        "/api/v1/generate", json={"prompt": "Hello", "stream": False}
    )

    assert response.status_code == 200
    log_entry = db_session.query(Log).one_or_none()
    assert log_entry is not None
    assert log_entry.response_status_code == 200


async def test_generate_api_error_logs_details(
    client: AsyncClient,
    mock_ollama_service: MagicMock,
    db_session: Session,
):
    """
    Test that a service-layer error from Ollama is handled by the global
    exception handler and that the error details are logged correctly.
    """
    mock_ollama_service.generate_response.side_effect = httpx.RequestError(
        "Ollama go boom", request=MagicMock(url="http://test.url/api")
    )

    response = await client.post(
        "/api/v1/generate", json={"prompt": "Cause an error", "stream": False}
    )

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert "Error connecting to upstream service" in response.json()["detail"]

    log_entry = db_session.query(Log).one_or_none()
    assert log_entry is not None
    assert log_entry.response_status_code == status.HTTP_502_BAD_GATEWAY
    assert log_entry.error_details is not None
    assert "Error connecting to upstream service" in log_entry.error_details
