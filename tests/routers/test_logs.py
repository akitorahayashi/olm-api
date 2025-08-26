import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from starlette import status

from src.db.models.log import Log

pytestmark = pytest.mark.asyncio


async def test_get_logs_returns_stored_logs(client: AsyncClient, db_session: Session):
    """
    Test that the /api/v1/logs endpoint returns logs stored in the database.
    """
    # Arrange: Create a sample log entry
    log_entry = Log(
        client_host="127.0.0.1",
        request_method="POST",
        request_path="/api/v1/generate",
        response_status_code=200,
        prompt="test prompt",
        generated_response="test response",
    )
    db_session.add(log_entry)
    db_session.commit()

    # Act
    response = await client.get("/api/v1/logs")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) == 1
    assert logs[0]["prompt"] == "test prompt"
    assert logs[0]["generated_response"] == "test response"
    assert logs[0]["response_status_code"] == 200


async def test_get_logs_empty_db_returns_empty_list(
    client: AsyncClient, db_session: Session
):
    """
    Test that the /api/v1/logs endpoint returns an empty list when no logs exist.
    """
    # Act
    response = await client.get("/api/v1/logs")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) == 0


async def test_view_logs_returns_html(client: AsyncClient):
    """
    Test that the /logs/view endpoint returns an HTML page.
    """
    # Act
    response = await client.get("/logs/view")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("text/html")
    # A simple check to ensure it looks like our HTML page
    assert "<h1>Request Logs</h1>" in response.text
