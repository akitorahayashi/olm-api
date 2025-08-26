from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from starlette import status

from src.api.v1.schemas import GenerateResponse

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_generate_uses_active_model(
    unit_test_client: AsyncClient, mock_ollama_service: MagicMock
):
    """
    Test that the /generate endpoint uses the active model provided by the mocked
    setting service and validates call arguments strictly.
    The active model name ('test-unit-model') is set in the unit_test_client fixture.
    """
    # Arrange
    prompt = "Test prompt"
    mock_ollama_service.generate_response.return_value = GenerateResponse(
        response="test response"
    )

    # Act
    response = await unit_test_client.post(
        "/api/v1/generate", json={"prompt": prompt, "stream": False}
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"response": "test response"}
    mock_ollama_service.generate_response.assert_called_once_with(
        prompt=prompt, model_name="test-unit-model", stream=False
    )


@patch("src.api.v1.services.setting_service.get_active_model", return_value=None)
async def test_generate_no_model_configured(
    mock_get_model: MagicMock,
    unit_test_client: AsyncClient,
    mock_ollama_service: MagicMock,
):
    """
    Test that a 503 error is returned if no model is configured.
    This test patches the setting_service to simulate no model being set,
    overriding the monkeypatch in the fixture for this specific test case.
    """
    # Act
    response = await unit_test_client.post(
        "/api/v1/generate", json={"prompt": "test", "stream": False}
    )

    # Assert
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "No generation model is currently configured" in response.json()["detail"]
    mock_ollama_service.generate_response.assert_not_called()
