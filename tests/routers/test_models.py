from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from starlette import status

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_get_models(client: AsyncClient, mock_ollama_client: MagicMock):
    """Test the GET /api/v1/models endpoint."""
    mock_response = {"models": [{"name": "test-model:latest"}]}
    mock_ollama_client.list.return_value = mock_response

    response = await client.get("/api/v1/models")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == mock_response
    mock_ollama_client.list.assert_called_once()


async def test_pull_model(client: AsyncClient, mock_ollama_client: MagicMock):
    """Test the POST /api/v1/models/pull endpoint."""
    model_name = "new-model:latest"
    mock_ollama_client.pull.return_value = {"status": "success"}

    response = await client.post("/api/v1/models/pull", json={"name": model_name})
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "success"}
    mock_ollama_client.pull.assert_called_once_with(model=model_name)


async def test_delete_model(client: AsyncClient, mock_ollama_client: MagicMock):
    """Test the DELETE /api/v1/models/{model_name} endpoint."""
    model_name = "test-model:latest"
    response = await client.delete(f"/api/v1/models/{model_name}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_ollama_client.delete.assert_called_once_with(model=model_name)


async def test_switch_active_model_success(
    client: AsyncClient, mock_ollama_client: MagicMock
):
    """Test successfully switching the active model."""
    model_name = "existing-model:latest"
    mock_ollama_client.list.return_value = {"models": [{"name": model_name}]}

    response = await client.post(f"/api/v1/models/switch/{model_name}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": f"Switched active model to {model_name}"}

    # Verify that the generate endpoint now uses this model
    mock_ollama_client.chat.return_value = {"message": {"content": "response"}}
    await client.post("/api/v1/generate", json={"prompt": "test", "stream": False})

    # Check that the `chat` method was called with the model we switched to
    mock_ollama_client.chat.assert_called_once()
    assert mock_ollama_client.chat.call_args.kwargs["model"] == model_name


async def test_switch_active_model_not_found(
    client: AsyncClient, mock_ollama_client: MagicMock
):
    """Test switching to a model that does not exist locally."""
    model_name = "non-existent-model:latest"
    mock_ollama_client.list.return_value = {
        "models": [{"name": "another-model:latest"}]
    }

    response = await client.post(f"/api/v1/models/switch/{model_name}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found locally" in response.json()["detail"]
