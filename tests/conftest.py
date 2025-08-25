import os
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.database import Base, create_db_session
from src.dependencies import logging as logging_dependency
from src.dependencies.common import get_ollama_client
from src.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up the test environment variables.
    """
    os.environ["BUILT_IN_OLLAMA_MODEL"] = "test-built-in-model"
    os.environ["DEFAULT_GENERATION_MODEL"] = "test-default-model"
    # Set a dummy DATABASE_URL. It's required by the Settings model,
    # but the actual test connection is patched to use in-memory SQLite.
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    yield


@pytest.fixture
def db_session(monkeypatch):
    """
    Provides a transactional scope around a test using an in-memory SQLite database.
    It creates the database, tables, and a session for each test function,
    and tears it all down afterward.
    """
    # Use in-memory SQLite for tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},  # Needed for SQLite
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    # Patch the function in the module where it is imported and used.
    # This ensures the logging middleware uses the test session.
    monkeypatch.setattr(logging_dependency, "create_db_session", lambda: db)

    # This override is for any other part of the app using Depends(create_db_session)
    app.dependency_overrides[create_db_session] = lambda: db

    try:
        yield db
    finally:
        db.rollback()
        db.close()
        # Drop tables
        Base.metadata.drop_all(bind=engine)
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
