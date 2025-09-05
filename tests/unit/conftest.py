from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from sdk.olm_api_client.mock import MockOllamaApiClient
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
    1.  **Setting Environment Variables**: It sets dummy environment variables
        to satisfy Pydantic settings validation without requiring actual database
        connection or configuration.

    2.  **Disabling Logging Middleware**: It uses `monkeypatch` to neutralize the
        `_safe_log` method of the `LoggingMiddleware`, preventing database writes.

    Yields:
        An `AsyncClient` configured for database-free testing.
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


@pytest.fixture
def fast_mock_client() -> MockOllamaApiClient:
    """
    Provides a fast MockOllamaApiClient with zero delay for unit testing.
    """
    return MockOllamaApiClient(token_delay=0)
