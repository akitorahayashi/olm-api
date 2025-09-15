import pytest

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


class TestGenerate:
    """Test generation validation and error handling."""

    async def test_missing_model(self, http_client, api_config):
        """Test validation error for missing model."""
        payload = {"messages": [{"role": "user", "content": "Hello"}]}

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 422

    async def test_empty_messages(self, http_client, api_config):
        """Test validation error for empty messages."""
        payload = {"model": api_config["model_name"], "messages": []}

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 422

    async def test_invalid_role(self, http_client, api_config):
        """Test validation error for invalid role."""
        payload = {
            "model": api_config["model_name"],
            "messages": [{"role": "invalid", "content": "Hello"}],
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 422

    async def test_field_aliases(self, http_client, api_config):
        """Test that field aliases work correctly."""
        payload = {
            "model_name": api_config["model_name"],  # Use alias instead of "model"
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 200

        data = response.json()
        assert data["model"] == api_config["model_name"]
