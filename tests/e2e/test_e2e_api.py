import os

import httpx
import pytest

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_generate_endpoint_e2e():
    """
    Performs an end-to-end test on the /api/v1/generate endpoint.

    This test sends a real HTTP request to the running API service and
    validates the response, simulating a basic user interaction.
    """
    host_port = os.getenv("HOST_PORT", "8000")
    model_name = os.getenv("BUILT_IN_OLLAMA_MODEL")
    assert model_name, "BUILT_IN_OLLAMA_MODEL environment variable must be set"

    generate_url = f"http://localhost:{host_port}/api/v1/generate"
    request_payload = {
        "prompt": "Why is the sky blue?",
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(generate_url, json=request_payload)

    # Assertions
    assert response.status_code == 200
    response_data = response.json()
    assert "response" in response_data
    assert isinstance(response_data["response"], str)
    assert len(response_data["response"]) > 0
