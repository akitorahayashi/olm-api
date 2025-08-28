from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

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
    Provides a test client for unit tests, isolated from the database.

    This fixture ensures database isolation through two main actions:
    1.  **Setting Environment Variables**: It sets dummy values for `DATABASE_URL`
        and `BUILT_IN_OLLAMA_MODEL` to satisfy Pydantic's settings validation
        without requiring a real environment file.

    2.  **Disabling Logging Middleware**: It neutralizes the `_safe_log` method
        of the `LoggingMiddleware` by replacing it with a function that does
        nothing. This prevents any attempts to write logs to the database during
        unit tests.

    Yields:
        An `AsyncClient` configured for database-free unit testing.
    """
    # 1. Set dummy environment variables to satisfy Pydantic settings
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
    monkeypatch.setenv("BUILT_IN_OLLAMA_MODEL", "test-built-in-model")

    # 2. Disable the DB logging middleware to prevent DB writes
    monkeypatch.setattr(
        db_logging_middleware.LoggingMiddleware,
        "_safe_log",
        lambda *args, **kwargs: None,
    )

    # 3. Yield the database-independent client
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
