import os
import subprocess
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from pytest_docker_tools import container, fetch

from src.dependencies.common import get_ollama_client
from src.main import app

# Define a new image for the test database
postgresql_image = fetch(repository="postgres:16-alpine")

# Define a container fixture for the test database
db_container = container(
    image="{postgresql_image.id}",
    ports={"5432/tcp": None},
    environment={
        "POSTGRES_USER": "testuser",
        "POSTGRES_PASSWORD": "testpassword",
        "POSTGRES_DB": "testdb",
    },
    scope="session",
)


@pytest.fixture(scope="session")
def db_url(db_container):
    """
    Returns the database URL for the test database container.
    Waits until the database is responsive.
    """
    port = db_container.ports["5432/tcp"][0]
    # The 'db_container.name' is not the correct hostname for the connection.
    # We should use 'localhost' as pytest-docker-tools maps the port to the host.
    url = f"postgresql+psycopg://testuser:testpassword@localhost:{port}/testdb"

    # Wait for the database to be ready
    db_container.exec_run(
        "pg_isready -U testuser -d testdb",
        # The command can fail while the database is starting up
        check=False,
    )
    return url


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment_and_db(db_url):
    """
    Set up the test environment:
    1. Set environment variables.
    2. Run database migrations.
    """
    os.environ["BUILT_IN_OLLAMA_MODEL"] = "test-built-in-model"
    os.environ["DEFAULT_GENERATION_MODEL"] = "test-default-model"
    os.environ["DATABASE_URL"] = db_url

    # Run Alembic migrations
    # We need to run this in a subprocess because Alembic's command-line tool
    # is the most reliable way to ensure migrations are applied correctly.
    # The env var DATABASE_URL will be picked up by alembic.ini's script.
    subprocess.run(["alembic", "upgrade", "head"], check=True)

    yield

    # Teardown (if any) can go here
    # The database container will be torn down automatically by pytest-docker-tools


@pytest.fixture
def mock_ollama_client():
    """
    Fixture to mock the Ollama client using FastAPI's dependency overrides.
    This ensures that any call to the get_ollama_client dependency returns a mock
    instead of a real client.
    """
    mock_client = MagicMock()
    # The actual ollama client methods are synchronous, so the mock methods
    # should be regular MagicMocks, not AsyncMocks. The service layer handles
    # running them in a threadpool.
    mock_client.chat = MagicMock()
    mock_client.list = MagicMock()
    mock_client.pull = MagicMock()
    mock_client.delete = MagicMock()

    # This is the override function that will be called by FastAPI
    def override_get_ollama_client():
        return mock_client

    # Apply the override
    app.dependency_overrides[get_ollama_client] = override_get_ollama_client

    yield mock_client  # The test will receive this mock instance

    # Clean up the override after the test is done
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
async def client():
    """
    Create an httpx.AsyncClient instance for the entire test module.
    This uses the ASGITransport to route requests directly to the app, without
    needing a running server.
    The `lifespan="on"` argument ensures that the app's startup and shutdown
    events are triggered during the test session.
    """
    transport = ASGITransport(app=app, lifespan="on")
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
