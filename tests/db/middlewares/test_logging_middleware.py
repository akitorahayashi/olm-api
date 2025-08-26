from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from src.api.v1.schemas import GenerateResponse
from src.api.v1.services import setting_service
from src.db.models.log import Log

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


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
    sse_chunks = [
        'data: {"response": "Once "}\n\n',
        'data: {"response": "upon "}\n\n',
        'data: {"response": "a time."}\n\n',
    ]
    stream_chunks_bytes = [c.encode("utf-8") for c in sse_chunks]
    full_response = "Once upon a time."

    async def stream_generator():
        for chunk in stream_chunks_bytes:
            yield chunk

    setting_service.set_active_model(db_session, "test-model")
    # The service returns a StreamingResponse for stream=True
    mock_ollama_service.generate_response.return_value = StreamingResponse(
        stream_generator(), media_type="text/event-stream; charset=utf-8"
    )

    # Act
    response = await client.post(
        "/api/v1/generate", json={"prompt": prompt, "stream": True}
    )

    # Assert
    assert response.status_code == 200

    # Ensure the client can consume the stream
    content = await response.aread()
    assert content == b"".join(stream_chunks_bytes)

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
