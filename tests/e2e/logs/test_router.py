import pytest
from httpx import AsyncClient
from starlette import status

pytestmark = pytest.mark.asyncio


async def test_get_logs_returns_empty_list(http_client: AsyncClient, api_config):
    """
    Test that the /logs/data endpoint returns data in the expected list format.
    Note: E2E tests cannot create test data directly in the database,
    so we test the endpoint behavior with an empty database.
    """
    base_url = api_config["base_url"]

    # Act
    response = await http_client.get(f"{base_url}/logs/data")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    logs = response.json()
    assert isinstance(logs, list)
    # In E2E tests, we cannot guarantee the database state, so we just check the structure


async def test_view_logs_returns_html(http_client: AsyncClient, api_config):
    """
    Test that the /logs/ endpoint returns an HTML page.
    """
    base_url = api_config["base_url"]

    # Act
    response = await http_client.get(f"{base_url}/logs/")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("text/html")
    # A simple check to ensure it looks like our HTML page
    assert "<h1>Request Logs</h1>" in response.text
