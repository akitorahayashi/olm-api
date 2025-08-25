from unittest.mock import MagicMock

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from starlette import status

from src.api.schemas.generate import GenerateResponse
from src.config.app_state import app_state
from src.db.models.log import Log

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_generate_uses_active_model(
    client: AsyncClient, mock_ollama_service: MagicMock, db_session: Session
):
    """
    Test that the /generate endpoint uses the model set in app_state and
    validates call arguments strictly.
    """
    # Arrange
    active_model = "my-active-model:latest"
    prompt = "Test prompt"
    app_state.set_current_model(active_model)
    # Mock the service to return a Pydantic model instance
    mock_ollama_service.generate_response.return_value = GenerateResponse(
        response="test response"
    )

    # Act
    response = await client.post(
        "/api/v1/generate", json={"prompt": prompt, "stream": False}
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"response": "test response"}
    # Verify that the service method was called with the correct arguments
    mock_ollama_service.generate_response.assert_called_once_with(
        prompt=prompt, model_name=active_model, stream=False
    )


async def test_generate_success_logs_metadata(
    client: AsyncClient,
    mock_ollama_service: MagicMock,
    db_session: Session,
):
    """Test that a successful request logs basic metadata."""
    # Arrange
    mock_ollama_service.generate_response.return_value = GenerateResponse(
        response="logged response"
    )

    # Act
    response = await client.post(
        "/api/v1/generate", json={"prompt": "Hello", "stream": False}
    )

    # Assert
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
    # Arrange
    mock_ollama_service.generate_response.side_effect = httpx.RequestError(
        "Ollama go boom", request=MagicMock(url="http://test.url/api")
    )

    # Act
    response = await client.post(
        "/api/v1/generate", json={"prompt": "Cause an error", "stream": False}
    )

    # Assert
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert "Error connecting to upstream service" in response.json()["detail"]

    log_entry = db_session.query(Log).one_or_none()
    assert log_entry is not None
    assert log_entry.response_status_code == status.HTTP_502_BAD_GATEWAY
    assert log_entry.error_details is not None
    assert "Error connecting to upstream service" in log_entry.error_details
