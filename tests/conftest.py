import os
from typing import AsyncGenerator, Generator, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config
from src.api.v1.services import setting_service
from src.api.v1.services.ollama_service import get_ollama_service
from src.db.database import create_db_session
from src.db.models.log import Log
from src.main import app
from src.middlewares import db_logging_middleware


def _is_xdist_master(config: pytest.Config) -> bool:
    """Check if the current process is the master node in an xdist session."""
    return not hasattr(config, "workerinput")


def _is_xdist_worker(config: pytest.Config) -> bool:
    """Check if the current process is a worker node in an xdist session."""
    return hasattr(config, "workerinput")


def _run_alembic_upgrade(db_url: str):
    """A helper function to run alembic migrations programmatically."""
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")


def pytest_addoption(parser):
    """Add a command line option to pytest to run database-dependent tests."""
    parser.addoption(
        "--db",
        action="store_true",
        default=False,
        help="run database-dependent tests",
    )


def pytest_configure(config: pytest.Config):
    """
    Pytest hook called before test session starts.

    If running in an xdist master process, it sets up environment variables,
    starts a PostgreSQL container, runs migrations, and stores the connection
    URL for worker processes.
    """
    # Skip database setup if --db option is not provided
    if not config.getoption("--db"):
        return

    if not _is_xdist_master(config):
        return

    # Load environment variables from .env file.
    # In the 'make test' flow, this .env is a symlink to .env.test.
    load_dotenv()

    # Set environment variables needed by Alembic and the application during tests.
    # This must be done before any application code that imports Settings is loaded.
    os.environ["BUILT_IN_OLLAMA_MODEL"] = "test-built-in-model"

    # Start the container using credentials from the environment
    container = PostgresContainer(
        "postgres:16-alpine",
        driver="psycopg",
        username=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD"),
        dbname=os.environ.get("POSTGRES_DB"),
    )
    container.start()

    # Store container instance and connection URL
    config.db_container = container
    db_url = container.get_connection_url()
    config.db_url = db_url
    os.environ["DATABASE_URL"] = db_url  # Set for the master process

    # Run migrations, which requires the DATABASE_URL env var
    _run_alembic_upgrade(db_url)

    # If xdist is active, save connection URL for workers
    if config.pluginmanager.is_registered("xdist"):
        # `getbasetemp` provides a reliable shared directory
        xdist_tmp_dir = config.getbasetemp().parent
        db_conn_file = xdist_tmp_dir / "db_url.txt"
        db_conn_file.write_text(db_url)


# def pytest_configure_node(node):
#     """
#     Pytest hook called to configure a worker node.
#
#     It reads the database connection URL from the file created by the master
#     process and stores it in the worker's config.
#     """
#     # Read the db_url from the file created by the master process
#     xdist_tmp_dir = node.config.getbasetemp().parent
#     db_conn_file = xdist_tmp_dir / "db_url.txt"
#     if db_conn_file.is_file():
#         node.config.db_url = db_conn_file.read_text()


def pytest_unconfigure(config: pytest.Config):
    """
    Pytest hook called after the entire test session finishes.

    If running in the master process, it stops the PostgreSQL container
    and cleans up the temporary connection file.
    """
    # Skip database teardown if --db option was not provided
    if not config.getoption("--db"):
        return

    if not _is_xdist_master(config):
        return

    # Stop the container if it was started
    if hasattr(config, "db_container"):
        config.db_container.stop()

    # Clean up the temp file used for xdist
    if config.pluginmanager.is_registered("xdist"):
        xdist_tmp_dir = config.getbasetemp().parent
        db_conn_file = xdist_tmp_dir / "db_url.txt"
        db_conn_file.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def db_url(request: pytest.FixtureRequest) -> str:
    """
    Fixture to provide the database URL to tests.

    It retrieves the URL that was set up by the `pytest_configure` or
    `pytest_configure_node` hooks.
    """
    return request.config.db_url


@pytest.fixture
def db_session(db_url: str, monkeypatch) -> Generator[Session, None, None]:
    """
    Provides a transactional scope for each test function.
    """
    engine: Optional[Engine] = None
    db: Optional[Session] = None
    try:
        engine = create_engine(db_url)
        TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine
        )
        db = TestingSessionLocal()

        monkeypatch.setattr(db_logging_middleware, "create_db_session", lambda: db)
        app.dependency_overrides[create_db_session] = lambda: db

        yield db
    finally:
        if db:
            db.rollback()
            db.query(Log).delete()
            db.commit()
            db.close()
        if engine:
            engine.dispose()  # Dispose of the engine's connection pool
        app.dependency_overrides.pop(create_db_session, None)


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
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an httpx.AsyncClient instance for each test function.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


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
