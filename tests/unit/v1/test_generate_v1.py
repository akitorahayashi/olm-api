from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from starlette import status

from src.api.v1.schemas import GenerateResponse

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_generate_with_model_name(
    unit_test_client: AsyncClient, mock_ollama_service: MagicMock
):
    """
    Test that the /generate endpoint uses the model specified in the request.
    """
    # Arrange
    prompt = "Test prompt"
    model_name = "test-model"
    mock_ollama_service.generate_response.return_value = GenerateResponse(
        think="", content="test response", response="test response"
    )

    # Act
    response = await unit_test_client.post(
        "/api/v1/chat",
        json={"prompt": prompt, "model_name": model_name, "stream": False},
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "think": "",
        "content": "test response",
        "response": "test response",
    }
    mock_ollama_service.generate_response.assert_called_once_with(
        prompt=prompt, model_name=model_name, stream=False, think=None
    )


async def test_generate_missing_model_name(
    unit_test_client: AsyncClient,
    mock_ollama_service: MagicMock,
):
    """
    Test that a 422 error is returned if model_name is not provided.
    """
    # Act
    response = await unit_test_client.post(
        "/api/v1/chat", json={"prompt": "test", "stream": False}
    )

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    mock_ollama_service.generate_response.assert_not_called()
