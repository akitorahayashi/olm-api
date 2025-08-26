from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.v1.services import setting_service
from src.api.v1.services.ollama_service import get_ollama_service
from src.main import app
from src.middlewares import db_logging_middleware


@pytest.fixture
def mock_ollama_service() -> MagicMock:
    """
    Fixture to mock the OllamaService using FastAPI's dependency overrides.
    """
    mock_service = MagicMock()
    mock_service.generate_response = AsyncMock()
    mock_service.list_models = AsyncMock()
    mock_service.pull_model = AsyncMock()
    mock_service.delete_model = AsyncMock()

    app.dependency_overrides[get_ollama_service] = lambda: mock_service
    yield mock_service
    app.dependency_overrides.pop(get_ollama_service, None)


@pytest.fixture
async def unit_test_client(monkeypatch) -> AsyncGenerator[AsyncClient, None]:
    """
    Provides a test client that operates independently of the database.

    This fixture achieves database isolation by:
    1.  **Mocking the Setting Service**: It uses `monkeypatch` to replace the
        `get_active_model` and `set_active_model` functions in the `setting_service`
        module. This prevents any database calls for model settings.

    2.  **Disabling Logging Middleware**: It uses `monkeypatch` to neutralize the
        `_safe_log` method of the `LoggingMiddleware`, preventing database writes.

    Yields:
        An `AsyncClient` configured for database-free testing.
    """
    # 1. Set dummy environment variables to satisfy Pydantic settings
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
    monkeypatch.setenv("BUILT_IN_OLLAMA_MODEL", "test-built-in-model")

    # 2. Mock setting_service functions to avoid DB queries
    monkeypatch.setattr(
        setting_service, "get_active_model", lambda db: "test-unit-model"
    )
    monkeypatch.setattr(setting_service, "set_active_model", lambda db, name: None)

    # 3. Disable the DB logging middleware to prevent DB writes
    monkeypatch.setattr(
        db_logging_middleware.LoggingMiddleware,
        "_safe_log",
        lambda *args, **kwargs: None,
    )

    # 4. Yield the database-independent client
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
