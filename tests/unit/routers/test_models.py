import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from starlette import status
from starlette.responses import StreamingResponse

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_get_models(
    unit_test_client: AsyncClient, mock_ollama_service: MagicMock
):
    """Test the GET /api/v1/models endpoint with a realistic mock."""
    # Arrange
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    mock_response = {
        "models": [
            {
                "model": "test-model:latest",
                "modified_at": now_iso,
                "size": 12345,
            }
        ]
    }
    mock_ollama_service.list_models.return_value = mock_response

    # Act
    response = await unit_test_client.get("/api/v1/models/")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["models"][0]["model"] == "test-model:latest"
    assert response_data["models"][0]["size"] == 12345
    mock_ollama_service.list_models.assert_called_once()


async def test_pull_model_no_stream(
    unit_test_client: AsyncClient, mock_ollama_service: MagicMock
):
    """Test the POST /api/v1/models/pull endpoint without streaming."""
    # Arrange
    model_name = "new-model:latest"
    mock_ollama_service.pull_model.return_value = {"status": "success"}

    # Act
    response = await unit_test_client.post(
        "/api/v1/models/pull", json={"name": model_name}, params={"stream": False}
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "success"}
    mock_ollama_service.pull_model.assert_called_once_with(model_name, False)


async def test_pull_model_streaming(
    unit_test_client: AsyncClient, mock_ollama_service: MagicMock
):
    """
    Test the POST /api/v1/models/pull endpoint with a realistic SSE stream.
    """
    # Arrange
    model_name = "streaming-model:latest"

    async def mock_sse_stream():
        yield f"data: {json.dumps({'status': 'pulling manifest'})}\n\n"
        yield f"data: {json.dumps({'status': 'verifying sha256:12345'})}\n\n"
        yield f"data: {json.dumps({'status': 'success'})}\n\n"

    mock_ollama_service.pull_model.return_value = StreamingResponse(
        mock_sse_stream(),
        media_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

    # Act
    response = await unit_test_client.post(
        "/api/v1/models/pull", json={"name": model_name}, params={"stream": True}
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("text/event-stream")

    mock_ollama_service.pull_model.assert_called_once_with(model_name, True)


async def test_delete_model(
    unit_test_client: AsyncClient, mock_ollama_service: MagicMock
):
    """Test the DELETE /api/v1/models/{model_name} endpoint."""
    model_name = "test-model:latest"
    await unit_test_client.delete(f"/api/v1/models/{model_name}")
    mock_ollama_service.delete_model.assert_called_once_with(model_name)


async def test_switch_active_model_success(
    unit_test_client: AsyncClient, mock_ollama_service: MagicMock
):
    """Test successfully switching the active model."""
    # Arrange
    model_name = "existing-model:latest"
    mock_ollama_service.list_models.return_value = {
        "models": [
            {
                "model": model_name,
                "modified_at": datetime.now(timezone.utc).isoformat(),
                "size": 12345,
            }
        ]
    }

    # Act
    response = await unit_test_client.post(f"/api/v1/models/switch/{model_name}")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": f"Switched active model to {model_name}"}
    mock_ollama_service.list_models.assert_called_once()


async def test_switch_active_model_not_found(
    unit_test_client: AsyncClient, mock_ollama_service: MagicMock
):
    """Test switching to a model that does not exist locally."""
    # Arrange
    model_name = "non-existent-model:latest"
    mock_ollama_service.list_models.return_value = {
        "models": [{"model": "another-model:latest"}]
    }

    # Act
    response = await unit_test_client.post(f"/api/v1/models/switch/{model_name}")

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found locally" in response.json()["detail"]


async def test_remove_model_fails_for_built_in_model(
    unit_test_client: AsyncClient, mock_ollama_service: MagicMock
):
    """
    Test that deleting the built-in model returns a 403 error.
    """
    # Arrange
    built_in_model = os.getenv("BUILT_IN_OLLAMA_MODEL")
    assert built_in_model is not None, "BUILT_IN_OLLAMA_MODEL must be set"

    # Act
    response = await unit_test_client.delete(f"/api/v1/models/{built_in_model}")

    # Assert
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "cannot be deleted" in response.json()["detail"]
    mock_ollama_service.delete_model.assert_not_called()
