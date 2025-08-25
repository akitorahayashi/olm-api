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

# Create a new engine and session for testing
TestingSessionLocal = None


@pytest.fixture(scope="session")
def db_container():
    """
    Starts and manages a PostgreSQL container for the test session.
    """
    with PostgresContainer(
        "postgres:16-alpine",
        username="testuser",
        password="testpassword",
        dbname="testdb",
    ) as postgres:
        yield postgres


@pytest.fixture(scope="session")
def db_url(db_container: PostgresContainer):
    """
    Returns the database URL from the running test container.
    This replaces psycopg2 with psycopg for compatibility with the project's driver.
    """
    return db_container.get_connection_url().replace("psycopg2", "psycopg")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment_and_db(db_url: str):
    """
    Set up the test environment:
    1. Set environment variables.
    2. Run database migrations programmatically.
    3. Configure the TestingSessionLocal.
    """
    global TestingSessionLocal
    os.environ["BUILT_IN_OLLAMA_MODEL"] = "test-built-in-model"
    os.environ["DEFAULT_GENERATION_MODEL"] = "test-default-model"
    os.environ["DATABASE_URL"] = db_url

    # Create the test database engine
    engine = create_engine(db_url)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Run Alembic migrations programmatically
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    yield


@pytest.fixture
def db_session(monkeypatch):
    """
    Provides a transactional scope around a test.
    It also patches the create_db_session function used by the logging middleware
    to ensure it uses the same transaction as the test.
    """
    db = TestingSessionLocal()

    # Patch the function in the module where it is imported and used.
    monkeypatch.setattr(logging_dependency, "create_db_session", lambda: db)

    # This override is kept in case other parts of the app use Depends(get_db)
    # although it's not strictly necessary for the failing tests.
    app.dependency_overrides[create_db_session] = lambda: db

    try:
        yield db
    finally:
        db.rollback()
        db.close()
        app.dependency_overrides.clear()


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
