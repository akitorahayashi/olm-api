import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config
from src.api.services.ollama import OllamaService
from src.db.database import create_db_session
from src.db.models.log import Log
from src.main import app
from src.middlewares import db_logging_middleware


@pytest.fixture(scope="session")
def db_container() -> PostgresContainer:
    """
    Fixture to create and manage a PostgreSQL container for the test session.
    The container is started once per session and torn down at the end.
    """
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as container:
        yield container


@pytest.fixture(scope="session")
def db_url(db_container: PostgresContainer) -> str:
    """
    Fixture to get the database connection URL from the container.
    """
    return db_container.get_connection_url()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment_and_db(db_url: str):
    """
    Auto-used session-scoped fixture to set up the test environment.
    """
    os.environ["BUILT_IN_OLLAMA_MODEL"] = "test-built-in-model"
    os.environ["DEFAULT_GENERATION_MODEL"] = "test-default-model"
    os.environ["DATABASE_URL"] = db_url

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    yield


@pytest.fixture
def db_session(db_url: str, monkeypatch):
    """
    Provides a transactional scope for each test function.
    """
    engine = create_engine(db_url)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    monkeypatch.setattr(db_logging_middleware, "create_db_session", lambda: db)
    app.dependency_overrides[create_db_session] = lambda: db

    try:
        yield db
    finally:
        db.rollback()
        db.query(Log).delete()
        db.commit()
        db.close()
        app.dependency_overrides.clear()


@pytest.fixture
def mock_ollama_service():
    """
    Fixture to mock the OllamaService using FastAPI's dependency overrides.
    """
    mock_service = MagicMock(spec=OllamaService)
    mock_service.generate_response = AsyncMock()
    mock_service.list_models = AsyncMock()
    mock_service.pull_model = AsyncMock()
    mock_service.delete_model = AsyncMock()

    app.dependency_overrides[OllamaService] = lambda: mock_service
    yield mock_service
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    """
    Create an httpx.AsyncClient instance for each test function.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
