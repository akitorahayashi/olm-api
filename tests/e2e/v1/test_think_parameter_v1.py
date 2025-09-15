import pytest

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


class TestV1ThinkParameter:
    """Test think parameter functionality in v1 API."""

    async def test_think_false_with_thinking_model(self, http_client, api_config):
        """Test think=false with a thinking-capable model."""
        payload = {
            "prompt": "What is 2+2?",
            "model_name": "qwen3:0.6b",  # thinking-capable model
            "think": False,
            "stream": False,
        }

        response = await http_client.post(api_config["v1_generate_url"], json=payload)
        assert response.status_code == 200

        data = response.json()
        # Check new response format
        assert "think" in data
        assert "content" in data
        assert "response" in data

        # Content should not contain thinking tags
        assert "<think>" not in data["content"]
        assert "</think>" not in data["content"]

        # Think field should be empty or not contain tags in content
        if data["think"]:
            assert "<think>" not in data["content"]

    async def test_think_true_with_thinking_model(self, http_client, api_config):
        """Test think=true with a thinking-capable model."""
        payload = {
            "prompt": "What is 2+2?",
            "model_name": "qwen3:0.6b",  # thinking-capable model
            "think": True,
            "stream": False,
        }

        response = await http_client.post(api_config["v1_generate_url"], json=payload)
        assert response.status_code == 200

        data = response.json()
        # Check new response format
        assert "think" in data
        assert "content" in data
        assert "response" in data
        assert isinstance(data["response"], str)

    async def test_think_false_with_non_thinking_model(self, http_client, api_config):
        """Test think=false with a non-thinking model (should be ignored)."""
        payload = {
            "prompt": "Hello",
            "model_name": api_config["model_name"],  # usually gemma3:270m
            "think": False,
            "stream": False,
        }

        response = await http_client.post(api_config["v1_generate_url"], json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "response" in data
        assert isinstance(data["response"], str)

    async def test_think_true_with_non_thinking_model(self, http_client, api_config):
        """Test think=true with a non-thinking model (should return error or be ignored)."""
        payload = {
            "prompt": "Hello",
            "model_name": api_config["model_name"],  # usually gemma3:270m
            "think": True,
            "stream": False,
        }

        response = await http_client.post(api_config["v1_generate_url"], json=payload)
        # This might return 200 (ignored) or error - depends on Ollama behavior
        # We test that the API handles it gracefully
        assert response.status_code in [200, 400, 422, 502]

    async def test_without_think_parameter(self, http_client, api_config):
        """Test that omitting think parameter works as before."""
        payload = {
            "prompt": "Hello",
            "model_name": api_config["model_name"],
            "stream": False,
        }

        response = await http_client.post(api_config["v1_generate_url"], json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "response" in data
        assert isinstance(data["response"], str)

    async def test_think_parameter_with_streaming(self, http_client, api_config):
        """Test think parameter with streaming response."""
        payload = {
            "prompt": "Hello",
            "model_name": api_config["model_name"],
            "think": False,
            "stream": True,
        }

        response = await http_client.post(api_config["v1_generate_url"], json=payload)
        assert response.status_code == 200
        assert (
            response.headers.get("content-type") == "text/event-stream; charset=utf-8"
        )
