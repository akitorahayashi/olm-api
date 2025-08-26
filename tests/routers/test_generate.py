from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import StreamingResponse

from src.api.v1.schemas import GenerateResponse
from src.api.v1.services import setting_service
from src.db.models.log import Log

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_generate_uses_active_model(
    client: AsyncClient, mock_ollama_service: MagicMock, db_session: Session
):
    """
    Test that the /generate endpoint uses the model set in the database and
    validates call arguments strictly.
    """
    # Arrange
    active_model = "my-active-model:latest"
    prompt = "Test prompt"
    setting_service.set_active_model(db_session, active_model)

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
    mock_ollama_service.generate_response.assert_called_once_with(
        prompt=prompt, model_name=active_model, stream=False
    )


@patch("src.api.v1.services.setting_service.get_active_model", return_value=None)
async def test_generate_no_model_configured(
    mock_get_model: MagicMock,
    client: AsyncClient,
    mock_ollama_service: MagicMock,
    db_session: Session,
):
    """
    Test that a 503 error is returned if no model is configured.
    This test patches the setting_service to simulate no model being set.
    """
    # Act
    response = await client.post(
        "/api/v1/generate", json={"prompt": "test", "stream": False}
    )

    # Assert
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "No generation model is currently configured" in response.json()["detail"]
    mock_ollama_service.generate_response.assert_not_called()


async def test_generate_logs_prompt_and_response(
    client: AsyncClient,
    mock_ollama_service: MagicMock,
    db_session: Session,
):
    """Test that a successful non-streaming request logs the prompt and response."""
    # Arrange
    prompt = "Hello, world!"
    expected_response = "This is a test response."
    setting_service.set_active_model(db_session, "test-model")
    mock_ollama_service.generate_response.return_value = GenerateResponse(
        response=expected_response
    )

    # Act
    response = await client.post(
        "/api/v1/generate", json={"prompt": prompt, "stream": False}
    )

    # Assert
    assert response.status_code == 200
    log_entry = db_session.query(Log).one()
    assert log_entry is not None
    assert log_entry.response_status_code == 200
    assert log_entry.prompt == prompt
    assert log_entry.generated_response == expected_response
    assert log_entry.error_details is None


async def test_generate_streaming_logs_full_response(
    client: AsyncClient,
    mock_ollama_service: MagicMock,
    db_session: Session,
):
    """Test that a successful streaming request logs the complete concatenated response."""
    # Arrange
    prompt = "Stream me a story."
    stream_chunks = [
        b'{"response": "Once "}',
        b'{"response": "upon "}',
        b'{"response": "a time."}',
    ]
    full_response = "Once upon a time."

    async def stream_generator():
        for chunk in stream_chunks:
            yield chunk

    setting_service.set_active_model(db_session, "test-model")
    # The service returns a StreamingResponse for stream=True
    mock_ollama_service.generate_response.return_value = StreamingResponse(
        stream_generator()
    )

    # Act
    response = await client.post(
        "/api/v1/generate", json={"prompt": prompt, "stream": True}
    )

    # Assert
    assert response.status_code == 200

    # Ensure the client can consume the stream
    content = await response.aread()
    assert content == b"".join(stream_chunks)

    # Verify the log entry
    log_entry = db_session.query(Log).one()
    assert log_entry is not None
    assert log_entry.response_status_code == 200
    assert log_entry.prompt == prompt
    assert log_entry.generated_response == full_response
    assert log_entry.error_details is None


async def test_generate_api_error_is_logged(
    client: AsyncClient,
    mock_ollama_service: MagicMock,
    db_session: Session,
):
    """
    Test that a service-layer error from Ollama is handled correctly and
    that the error details are logged.
    """
    # Arrange
    prompt = "This will cause an error."
    error_message = "Ollama go boom"
    setting_service.set_active_model(db_session, "test-model")
    mock_ollama_service.generate_response.side_effect = Exception(error_message)

    # Act
    # The global exception handler will catch the exception and return a 500
    # In a real scenario, more specific exceptions would be caught.
    with pytest.raises(Exception, match=error_message):
        await client.post("/api/v1/generate", json={"prompt": prompt, "stream": False})

    # Assert
    log_entry = db_session.query(Log).one()
    assert log_entry is not None
    assert (
        log_entry.response_status_code == 500
    )  # Default code for unhandled exceptions
    assert log_entry.prompt == prompt
    assert log_entry.generated_response is None
    assert error_message in log_entry.error_details
