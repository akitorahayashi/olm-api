"""
Common fixtures for all test modules.
This file contains fixtures that are shared across different test types.
"""

import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient

from sdk.olm_api_client.v1.mock_client import MockOlmClientV1
from src.api.v1.ollama_service_v1 import OllamaServiceV1
from src.api.v2.ollama_service_v2 import OllamaServiceV2
from src.main import app
from src.middlewares import db_logging_middleware

# Load environment variables from .env file
load_dotenv()


# =============================================================================
# Common Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_client():
    """
    Provides a MockOlmClientV1 with zero delay and predictable responses for fast testing.
    """
    predictable_responses = [
        "Test response 1",
        "Test response 2",
        "Test response 3",
        "Test response 4",
        "Test response 5",
    ]
    return MockOlmClientV1(token_delay=0, responses=predictable_responses)


@pytest.fixture
def slow_mock_client():
    """
    Provides a MockOlmClientV1 with realistic delay and predictable responses for testing streaming behavior.
    """
    predictable_responses = [
        "Slow test response 1",
        "Slow test response 2",
        "Slow test response 3",
    ]
    return MockOlmClientV1(token_delay=0.01, responses=predictable_responses)


@pytest.fixture
def fast_mock_client():
    """
    Provides a fast MockOlmClientV1 with zero delay for unit testing.
    """
    return MockOlmClientV1(token_delay=0)


@pytest.fixture
def custom_response_client():
    """
    Provides a MockOlmClientV1 with custom responses for specific test scenarios.
    """

    def _create_client(responses):
        return MockOlmClientV1(token_delay=0, responses=responses)

    return _create_client


# =============================================================================
# Service Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_ollama_service() -> MagicMock:
    """
    Fixture to mock the v1 OllamaService using FastAPI's dependency overrides.
    """
    mock_service = MagicMock()
    mock_service.generate_response = AsyncMock()
    mock_service.list_models = AsyncMock()
    mock_service.pull_model = AsyncMock()
    mock_service.delete_model = AsyncMock()

    app.dependency_overrides[OllamaServiceV1.get_instance] = lambda: mock_service
    yield mock_service
    app.dependency_overrides.pop(OllamaServiceV1.get_instance, None)


@pytest.fixture
def mock_ollama_service_v2() -> MagicMock:
    """
    Fixture to mock the v2 OllamaServiceV2 using FastAPI's dependency overrides.
    """
    mock_service = MagicMock()
    mock_service.chat_completion = AsyncMock()
    mock_service.list_models = AsyncMock()

    app.dependency_overrides[OllamaServiceV2.get_instance] = lambda: mock_service
    yield mock_service
    app.dependency_overrides.pop(OllamaServiceV2.get_instance, None)


# =============================================================================
# Test Client Fixtures
# =============================================================================


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
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("BUILT_IN_OLLAMA_MODELS", "test-built-in-model")

    # 2. Disable the DB logging middleware to prevent DB writes
    monkeypatch.setattr(
        db_logging_middleware.LoggingMiddleware,
        "_safe_log",
        lambda self, *args, **kwargs: None,
    )

    # 3. Yield the database-independent client
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# =============================================================================
# Performance Test Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def load_prompt() -> str:
    """
    Load prompt from the shared prompt.txt file.
    """
    prompt_path = os.path.join(os.path.dirname(__file__), "perf", "prompt.txt")
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()


@pytest.fixture(scope="session")
def get_model_name() -> str:
    """
    Get the model name. Configure the model name here manually.
    """
    # Manually configure the model name here
    model_name = "qwen3:1.7b"
    return model_name


# =============================================================================
# Environment Configuration
# =============================================================================

# Set environment variables for Docker Compose
os.environ["HOST_BIND_IP"] = os.getenv("HOST_BIND_IP", "127.0.0.1")
os.environ["TEST_PORT"] = os.getenv("TEST_PORT", "8002")
os.environ["BUILT_IN_OLLAMA_MODELS"] = os.getenv("BUILT_IN_OLLAMA_MODELS", "qwen3:0.6b")
