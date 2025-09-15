import pytest

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


class TestThinkParameter:
    """Test think parameter functionality."""

    async def test_think_false_with_thinking_model(self, http_client, api_config):
        """Test think=false with a thinking-capable model."""
        payload = {
            "model": "qwen3:0.6b",  # thinking-capable model
            "messages": [{"role": "user", "content": "What is 2+2?"}],
            "think": False,
            "stream": False,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 200

        data = response.json()
        # Response should not contain thinking tags
        content = data["choices"][0]["message"]["content"]
        assert "<think>" not in content
        assert "</think>" not in content

    async def test_think_true_with_thinking_model(self, http_client, api_config):
        """Test think=true with a thinking-capable model."""
        payload = {
            "model": "qwen3:0.6b",  # thinking-capable model
            "messages": [{"role": "user", "content": "What is 2+2?"}],
            "think": True,
            "stream": False,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 200

        response.json()
        # Response may contain thinking tags
        # We just verify the request was processed successfully

    async def test_think_false_with_non_thinking_model(self, http_client, api_config):
        """Test think=false with a non-thinking model (should be ignored)."""
        payload = {
            "model": api_config["model_name"],  # usually gemma3:270m
            "messages": [{"role": "user", "content": "Hello"}],
            "think": False,
            "stream": False,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 200

        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0

    async def test_think_true_with_non_thinking_model(self, http_client, api_config):
        """Test think=true with a non-thinking model (should return error or be ignored)."""
        payload = {
            "model": api_config["model_name"],  # usually gemma3:270m
            "messages": [{"role": "user", "content": "Hello"}],
            "think": True,
            "stream": False,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        # This might return 200 (ignored) or error - depends on Ollama behavior
        # We test that the API handles it gracefully
        assert response.status_code in [200, 400, 422]

    async def test_without_think_parameter(self, http_client, api_config):
        """Test that omitting think parameter works as before."""
        payload = {
            "model": api_config["model_name"],
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 200

        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0

    async def test_think_parameter_with_streaming(self, http_client, api_config):
        """Test think parameter with streaming response."""
        payload = {
            "model": api_config["model_name"],
            "messages": [{"role": "user", "content": "Hello"}],
            "think": False,
            "stream": True,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 200
        assert (
            response.headers.get("content-type") == "text/event-stream; charset=utf-8"
        )
