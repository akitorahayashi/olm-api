import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from alembic.config import Config
from src.api.v1.ollama_service_v1 import OllamaServiceV1
from src.db.database import create_db_session
from src.logs.models import Log
from src.main import app
from src.middlewares import db_logging_middleware


@pytest.fixture(scope="session", autouse=True)
def db_setup(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Generator[str, None, None]:
    """
    Session-scoped fixture to manage the test SQLite database.

    Creates a temporary SQLite database for testing and runs migrations.
    """
    # Set a dummy model for DB tests, which don't need a real one.
    # This is required for Alembic's env.py to validate settings.
    os.environ["BUILT_IN_OLLAMA_MODELS"] = "test-db-model"
    # Enable API logging for DB middleware tests
    os.environ["API_LOGGING_ENABLED"] = "true"

    # Create temporary SQLite database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"
    db_url_value = f"sqlite:///{db_path}"

    os.environ["DATABASE_URL"] = db_url_value
    print(f"\n✅ SQLite test database created: {db_url_value}")
    print("🔄 Running database migrations...")

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url_value)
    command.upgrade(alembic_cfg, "head")
    print("✅ Database migrations completed!")

    yield db_url_value

    # Cleanup
    if db_path.exists():
        db_path.unlink()


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
        engine = create_engine(
            db_url,
            connect_args=(
                {"check_same_thread": False} if db_url.startswith("sqlite") else {}
            ),
        )
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

    app.dependency_overrides[OllamaServiceV1.get_instance] = lambda: mock_service
    yield mock_service
    app.dependency_overrides.pop(OllamaServiceV1.get_instance, None)


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
