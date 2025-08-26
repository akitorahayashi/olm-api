from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from src.api.v1.services import setting_service

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_switch_active_model_success(
    client: AsyncClient, mock_ollama_service: MagicMock, db_session: Session
):
    """Test successfully switching the active model and verifying DB persistence."""
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
    response = await client.post(f"/api/v1/models/switch/{model_name}")

    # Assert
    assert response.status_code == 200
    # Verify that the change was persisted in the database
    active_model_from_db = setting_service.get_active_model(db_session)
    assert active_model_from_db == model_name


async def test_switch_active_model_last_writer_wins(
    client: AsyncClient, mock_ollama_service: MagicMock, db_session: Session
):
    """
    Test that concurrent model switches result in the last write persisting.
    """
    # Arrange
    model_1 = "model-one:latest"
    model_2 = "model-two:latest"

    # Both models are available locally
    mock_ollama_service.list_models.return_value = {
        "models": [
            {"model": model_1, "modified_at": "...", "size": 1},
            {"model": model_2, "modified_at": "...", "size": 2},
        ]
    }

    # Act: Switch to the first model, then immediately to the second.
    await client.post(f"/api/v1/models/switch/{model_1}")
    await client.post(f"/api/v1/models/switch/{model_2}")

    # Assert
    # Verify that the final active model in the database is the second one.
    active_model_from_db = setting_service.get_active_model(db_session)
    assert active_model_from_db == model_2
