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
from src.api.v1.services.ollama_service import get_ollama_service
from src.db.database import create_db_session
from src.db.models.log import Log
from src.main import app
from src.middlewares import db_logging_middleware


def _is_xdist_master(config: pytest.Config) -> bool:
    """Check if the current process is the master node in an xdist session."""
    return not hasattr(config, "workerinput")


def pytest_configure(config: pytest.Config):
    """
    Pytest hook called before test session starts.

    If running in an xdist master process, it sets up environment variables,
    starts a PostgreSQL container, runs migrations, and stores the connection
    URL for worker processes.
    """
    if not config.getoption("--db"):
        return

    if not _is_xdist_master(config):
        return

    load_dotenv()
    os.environ["BUILT_IN_OLLAMA_MODEL"] = "test-built-in-model"

    container = PostgresContainer(
        "postgres:16-alpine",
        driver="psycopg",
        username=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD"),
        dbname=os.environ.get("POSTGRES_DB"),
    )
    container.start()

    config.db_container = container
    db_url = container.get_connection_url()
    config.db_url = db_url
    os.environ["DATABASE_URL"] = db_url

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    if config.pluginmanager.is_registered("xdist"):
        xdist_tmp_dir = config.getbasetemp().parent
        db_conn_file = xdist_tmp_dir / "db_url.txt"
        db_conn_file.write_text(db_url)


def pytest_unconfigure(config: pytest.Config):
    """
    Pytest hook called after the entire test session finishes.
    """
    if not config.getoption("--db"):
        return

    if not _is_xdist_master(config):
        return

    if hasattr(config, "db_container"):
        config.db_container.stop()

    if config.pluginmanager.is_registered("xdist"):
        xdist_tmp_dir = config.getbasetemp().parent
        db_conn_file = xdist_tmp_dir / "db_url.txt"
        db_conn_file.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def db_url(request: pytest.FixtureRequest) -> str:
    """
    Fixture to provide the database URL to tests.
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
            engine.dispose()
        app.dependency_overrides.pop(create_db_session, None)


@pytest.fixture
def mock_ollama_service() -> MagicMock:
    """
    Fixture to mock the OllamaService using FastAPI's dependency overrides.
    This is also needed for DB tests that hit the API but shouldn't call Ollama.
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
async def client(db_session: Session) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an httpx.AsyncClient instance that is properly configured for
    database-dependent tests.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
