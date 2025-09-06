import os

import httpx
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
def api_config():
    """Provides API configuration for E2E tests."""
    host_port = os.getenv("TEST_PORT", "8002")
    model_name = os.getenv("BUILT_IN_OLLAMA_MODEL", "qwen3:0.6b")
    generate_url = f"http://localhost:{host_port}/api/v1/generate"
    return {"url": generate_url, "model": model_name}


async def test_generate_endpoint_default_e2e(api_config):
    """
    E2E test for the /api/v1/generate endpoint with default behavior (think=True).
    """
    request_payload = {
        "prompt": "Why is the sky blue?",
        "model_name": api_config["model"],
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(api_config["url"], json=request_payload)

    assert response.status_code == 200
    response_data = response.json()
    assert "response" in response_data
    assert isinstance(response_data["response"], str)
    # By default, think should be true
    assert "<think>" in response_data["response"]
    assert "</think>" in response_data["response"]


async def test_generate_endpoint_with_think_true_e2e(api_config):
    """
    E2E test for the /api/v1/generate endpoint with think: true.
    """
    request_payload = {
        "prompt": "Explain general relativity in simple terms.",
        "model_name": api_config["model"],
        "stream": False,
        "think": True,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(api_config["url"], json=request_payload)

    assert response.status_code == 200
    response_data = response.json()
    assert "response" in response_data
    assert isinstance(response_data["response"], str)
    assert "<think>" in response_data["response"]
    assert "</think>" in response_data["response"]


async def test_generate_endpoint_with_think_false_e2e(api_config):
    """
    E2E test for the /api/v1/generate endpoint with think: false.
    """
    request_payload = {
        "prompt": "What is the capital of France?",
        "model_name": api_config["model"],
        "stream": False,
        "think": False,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(api_config["url"], json=request_payload)

    assert response.status_code == 200
    response_data = response.json()
    assert "response" in response_data
    assert isinstance(response_data["response"], str)
    assert "<think>" not in response_data["response"]
    assert "</think>" not in response_data["response"]
