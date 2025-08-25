import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from starlette import status

from src.api.schemas.generate import GenerateResponse

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_get_models(client: AsyncClient, mock_ollama_service: MagicMock):
    """Test the GET /api/v1/models endpoint with a realistic mock."""
    # Arrange
    # Pydantic serializes datetimes to a specific ISO format, so we match it.
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    mock_response = {
        "models": [
            {
                "name": "test-model:latest",
                "modified_at": now_iso,
                "size": 12345,
            }
        ]
    }
    mock_ollama_service.list_models.return_value = mock_response

    # Act
    response = await client.get("/api/v1/models/")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    # Pydantic will format the datetime string in the response, so we compare against that.
    response_data = response.json()
    assert response_data["models"][0]["name"] == "test-model:latest"
    assert response_data["models"][0]["size"] == 12345
    mock_ollama_service.list_models.assert_called_once()


async def test_pull_model_no_stream(client: AsyncClient, mock_ollama_service: MagicMock):
    """Test the POST /api/v1/models/pull endpoint without streaming."""
    # Arrange
    model_name = "new-model:latest"
    mock_ollama_service.pull_model.return_value = {"status": "success"}

    # Act
    response = await client.post(
        "/api/v1/models/pull", json={"name": model_name}, params={"stream": False}
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "success"}
    # The `stream` parameter is passed positionally by FastAPI from the query params.
    mock_ollama_service.pull_model.assert_called_once_with(model_name, False)


async def test_pull_model_streaming(client: AsyncClient, mock_ollama_service: MagicMock):
    """Test the POST /api/v1/models/pull endpoint with SSE streaming."""
    # Arrange
    model_name = "streaming-model:latest"
    mock_ollama_service.pull_model.return_value = "mocked streaming response"

    # Act
    response = await client.post(
        "/api/v1/models/pull", json={"name": model_name}, params={"stream": True}
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    # The `stream` parameter is passed positionally.
    mock_ollama_service.pull_model.assert_called_once_with(model_name, True)


async def test_delete_model(client: AsyncClient, mock_ollama_service: MagicMock):
    """Test the DELETE /api/v1/models/{model_name} endpoint."""
    model_name = "test-model:latest"
    await client.delete(f"/api/v1/models/{model_name}")
    mock_ollama_service.delete_model.assert_called_once_with(model_name)


async def test_switch_active_model_success(
    client: AsyncClient, mock_ollama_service: MagicMock
):
    """Test successfully switching the active model."""
    model_name = "existing-model:latest"
    mock_ollama_service.list_models.return_value = {
        "models": [
            {
                "name": model_name,
                "modified_at": datetime.now(timezone.utc).isoformat(),
                "size": 12345,
            }
        ]
    }

    response = await client.post(f"/api/v1/models/switch/{model_name}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": f"Switched active model to {model_name}"}

    # Verify that the generate endpoint now uses this model
    mock_ollama_service.generate_response.return_value = GenerateResponse(
        response="response from switched model"
    )
    await client.post(
        "/api/v1/generate", json={"prompt": "test", "stream": False}
    )

    mock_ollama_service.generate_response.assert_called_once_with(
        prompt="test", model_name=model_name, stream=False
    )


async def test_switch_active_model_not_found(
    client: AsyncClient, mock_ollama_service: MagicMock
):
    """Test switching to a model that does not exist locally."""
    model_name = "non-existent-model:latest"
    mock_ollama_service.list_models.return_value = {
        "models": [{"name": "another-model:latest"}]
    }

    response = await client.post(f"/api/v1/models/switch/{model_name}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found locally" in response.json()["detail"]
