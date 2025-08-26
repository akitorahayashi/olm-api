import os
import time
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


@pytest.fixture(scope="session", autouse=True)
def db_setup(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Generator[str, None, None]:
    """
    Session-scoped fixture to manage the test database container.

    This fixture is automatically used by all tests in this directory and its
    subdirectories. It handles xdist by having the master node create the DB
    container and share its connection URL with worker nodes via a temporary file.
    """
    is_master = not hasattr(request.config, "workerinput")

    db_conn_file = None
    if request.config.pluginmanager.is_registered("xdist"):
        # In xdist, tmp_path_factory provides a shared directory for the session.
        root_tmp_dir = tmp_path_factory.getbasetemp().parent
        db_conn_file = root_tmp_dir / "db_url.txt"

    container: Optional[PostgresContainer] = None
    db_url_value: str

    if is_master:
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
        db_url_value = container.get_connection_url()
        os.environ["DATABASE_URL"] = db_url_value

        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", "alembic")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url_value)
        command.upgrade(alembic_cfg, "head")

        if db_conn_file:
            db_conn_file.write_text(db_url_value)
    else:  # worker node
        if not db_conn_file:
            pytest.fail(
                "xdist is running but the db_conn_file path could not be determined."
            )

        timeout = 20
        start_time = time.time()
        while not db_conn_file.exists():
            if time.time() - start_time > timeout:
                pytest.fail(
                    f"Worker could not find db_url.txt after {timeout} seconds."
                )
            time.sleep(0.1)
        db_url_value = db_conn_file.read_text()

    yield db_url_value

    if is_master and container:
        container.stop()
        if db_conn_file and db_conn_file.exists():
            db_conn_file.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def db_url(db_setup: str) -> str:
    """
    Fixture to provide the database URL to tests.
    It receives the URL from the session-scoped db_setup fixture.
    """
    return db_setup


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
