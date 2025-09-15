import json

import pytest

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


class TestGenerate:
    """Test streaming generation functionality."""

    async def test_streaming_completion(self, http_client, api_config):
        """Test streaming chat completion."""
        payload = {
            "model": api_config["model_name"],
            "messages": [{"role": "user", "content": "Count from 1 to 5"}],
            "stream": True,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        chunks = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                if data_str:
                    try:
                        chunk = json.loads(data_str)
                        chunks.append(chunk)
                    except json.JSONDecodeError:
                        continue

        assert len(chunks) > 0
        # Check first chunk has role
        first_chunk = chunks[0]
        assert first_chunk["object"] == "chat.completion.chunk"
        assert "choices" in first_chunk
        assert first_chunk["choices"][0]["delta"].get("role") == "assistant"

        # Check that we got content chunks
        content_chunks = [
            chunk
            for chunk in chunks
            if "choices" in chunk
            and len(chunk["choices"]) > 0
            and chunk["choices"][0]["delta"].get("content")
        ]
        assert len(content_chunks) > 0
