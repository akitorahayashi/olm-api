from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from olm_api.api.v1.ollama_service_v1 import GenerateResponse
from olm_api.logs.models import Log

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
    model_name = "test-model"
    mock_ollama_service.generate_response.return_value = GenerateResponse(
        response=expected_response
    )

    # Act
    response = await client.post(
        "/api/v1/chat",
        json={"prompt": prompt, "model_name": model_name, "stream": False},
    )

    # Assert
    assert response.status_code == 200
    log_entry = db_session.query(Log).order_by(Log.id.desc()).first()
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
    model_name = "test-model"
    sse_chunks = [
        'data: {"response": "Once "}\n\n',
        'data: {"response": "upon "}\n\n',
        'data: {"response": "a time."}\n\n',
    ]
    stream_chunks_bytes = [c.encode("utf-8") for c in sse_chunks]

    async def stream_generator():
        for chunk in stream_chunks_bytes:
            yield chunk

    # The service returns a StreamingResponse for stream=True
    mock_ollama_service.generate_response.return_value = StreamingResponse(
        stream_generator(), media_type="text/event-stream; charset=utf-8"
    )

    # Act
    response = await client.post(
        "/api/v1/chat",
        json={"prompt": prompt, "model_name": model_name, "stream": True},
    )

    # Assert
    assert response.status_code == 200

    # Ensure the client can consume the stream
    content = await response.aread()
    assert content == b"".join(stream_chunks_bytes)

    # Verify the log entry
    log_entry = db_session.query(Log).order_by(Log.id.desc()).first()
    assert log_entry is not None
    assert log_entry.response_status_code == 200
    assert log_entry.prompt == prompt
    assert log_entry.generated_response == "[stream omitted]"
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
    model_name = "test-model"
    mock_ollama_service.generate_response.side_effect = Exception(error_message)

    # Act
    # The global exception handler will catch the exception and return a 500
    response = await client.post(
        "/api/v1/chat",
        json={"prompt": prompt, "model_name": model_name, "stream": False},
    )

    # Assert the response status code
    assert response.status_code == 500

    # Assert
    log_entry = db_session.query(Log).order_by(Log.id.desc()).first()
    assert log_entry is not None
    assert (
        log_entry.response_status_code == 500
    )  # Default code for unhandled exceptions
    assert log_entry.prompt == prompt
    assert log_entry.generated_response is None
    assert log_entry.error_details is not None
    assert error_message in log_entry.error_details
