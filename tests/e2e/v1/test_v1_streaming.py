import json

import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


class TestStreaming:
    """Test v1 streaming generation functionality."""

    async def test_streaming_generation(self, http_client, api_config):
        """
        Test streaming generation functionality for v1 API.

        This test verifies that the streaming endpoint returns proper
        Server-Sent Events (SSE) format with incremental response chunks.
        """
        request_payload = {
            "prompt": "Count from 1 to 5",
            "model_name": api_config["model_name"],
            "stream": True,
        }

        response = await http_client.post(
            api_config["v1_generate_url"], json=request_payload
        )

        # Debug output for failed requests
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response body: {response.text}")

        # Verify response is streaming
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Collect streaming chunks
        chunks = []
        full_content = []

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:].strip()  # Remove "data: " prefix
                if data_str:
                    try:
                        chunk = json.loads(data_str)
                        chunks.append(chunk)

                        # Collect content for full response reconstruction
                        if "response" in chunk and chunk["response"]:
                            full_content.append(chunk["response"])
                    except json.JSONDecodeError:
                        continue

        # Verify we received chunks
        assert len(chunks) > 0, "Should receive at least one streaming chunk"

        # Verify chunk structure
        for chunk in chunks:
            assert (
                "response" in chunk
            ), f"Each chunk should have 'response' field, got: {chunk}"
            assert isinstance(
                chunk["response"], str
            ), "Response content should be string"

        # Verify we got some actual content
        full_response = "".join(full_content)
        assert (
            len(full_response) > 0
        ), "Should receive some content in streaming response"

        # Verify the response makes sense for the prompt (should contain numbers)
        assert any(
            char.isdigit() for char in full_response
        ), "Response should contain numbers for counting prompt"
