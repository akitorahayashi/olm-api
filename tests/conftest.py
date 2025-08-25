import os
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config
from src.db.database import create_db_session
from src.dependencies import logging as logging_dependency
from src.dependencies.common import get_ollama_client
from src.main import app
from src.models.log import Log


@pytest.fixture(scope="session")
def db_container() -> PostgresContainer:
    """
    Fixture to create and manage a PostgreSQL container for the test session.
    The container is started once per session and torn down at the end.
    """
    # The 'with' statement ensures the container is automatically stopped
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as container:
        yield container


@pytest.fixture(scope="session")
def db_url(db_container: PostgresContainer) -> str:
    """
    Fixture to get the database connection URL from the container.
    This URL is used to connect to the test database.
    """
    return db_container.get_connection_url()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment_and_db(db_url: str):
    """
    Auto-used session-scoped fixture to set up the test environment.
    It sets environment variables and runs Alembic migrations.
    """
    # Set environment variables for the test session
    os.environ["BUILT_IN_OLLAMA_MODEL"] = "test-built-in-model"
    os.environ["DEFAULT_GENERATION_MODEL"] = "test-default-model"
    os.environ["DATABASE_URL"] = db_url

    # Set up Alembic configuration programmatically.
    # This is necessary because the test environment doesn't use an alembic.ini file.
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # Run migrations to set up the schema
    command.upgrade(alembic_cfg, "head")

    yield

    # Teardown logic can be added here if needed,
    # but the container fixture handles DB teardown.


@pytest.fixture
def db_session(db_url: str, monkeypatch):
    """
    Provides a transactional scope for each test function.
    It creates a new session for each test, patches the dependency,
    and rolls back the transaction after the test is complete.
    Crucially, it also cleans up any data committed by the application
    (e.g., by the logging middleware) to ensure test isolation.
    """
    engine = create_engine(db_url)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    # Patch the create_db_session dependency to use the test session
    monkeypatch.setattr(logging_dependency, "create_db_session", lambda: db)
    app.dependency_overrides[create_db_session] = lambda: db

    try:
        yield db
    finally:
        # Rollback any uncommitted changes from the test itself
        db.rollback()
        # Clean up any committed data to ensure isolation between tests
        db.query(Log).delete()
        db.commit()
        db.close()
        app.dependency_overrides.clear()  # Clear overrides after the test


@pytest.fixture
def mock_ollama_client():
    """
    Fixture to mock the Ollama client using FastAPI's dependency overrides.
    """
    mock_client = MagicMock()
    mock_client.chat = MagicMock()
    mock_client.list = MagicMock()
    mock_client.pull = MagicMock()
    mock_client.delete = MagicMock()

    def override_get_ollama_client():
        return mock_client

    app.dependency_overrides[get_ollama_client] = override_get_ollama_client
    yield mock_client
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
