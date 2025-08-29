import os

import httpx
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_generate_endpoint_e2e():
    """
    Performs an end-to-end test on the /api/v1/generate endpoint.

    This test sends a real HTTP request to the running API service and
    validates the response, simulating a basic user interaction.
    """
    host_port = os.getenv("TEST_PORT", "8002")
    model_name = os.getenv("BUILT_IN_OLLAMA_MODEL", "qwen3:0.6b")

    generate_url = f"http://localhost:{host_port}/api/v1/generate"
    request_payload = {
        "prompt": "Why is the sky blue?",
        "model_name": model_name,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(generate_url, json=request_payload)

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
