
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


class TestGenerate:
    """Test v1 generate endpoint functionality."""

    async def test_basic_generation(self, http_client, api_config):
        """
        Performs an end-to-end test on the /api/v1/generate endpoint.

        This test sends a real HTTP request to the running API service and
        validates the response, simulating a basic user interaction.
        """
        request_payload = {
            "prompt": "Why is the sky blue?",
            "model_name": api_config["model_name"],
            "stream": False,
        }

        response = await http_client.post(
            api_config["v1_generate_url"], json=request_payload
        )

        # Debug output for failed requests
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response body: {response.text}")

        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert "response" in response_data
        assert isinstance(response_data["response"], str)
        assert len(response_data["response"]) > 0
