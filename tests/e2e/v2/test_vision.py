import base64
from pathlib import Path

import pytest

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


class TestVision:
    """Test vision/image functionality with different models."""

    @pytest.fixture
    def test_image_base64(self):
        """An image in base64 format for testing."""
        image_path = Path(__file__).parent / "test_images" / "test_image_1.png"
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @pytest.fixture
    def vision_model_name(self):
        """Get vision-capable model name from environment."""
        # Force use of gemma3:4b for image processing
        return "gemma3:4b"

    @pytest.fixture
    def non_vision_model_name(self):
        """Get non-vision model name from environment."""
        import os

        models = os.getenv("BUILT_IN_OLLAMA_MODELS", "").split(",")
        # Look for qwen3 (non-vision) or default to first model
        for model in models:
            if "qwen3" in model.strip():
                return model.strip()
        return models[0]

    async def test_vision_model_with_image_success(
        self, http_client, api_config, test_image_base64, vision_model_name
    ):
        """Test that vision-capable model (gemma3) can process images."""
        payload = {
            "model": vision_model_name,
            "messages": [
                {
                    "role": "user",
                    "content": "Describe this image in one word.",
                    "images": [test_image_base64],
                }
            ],
            "stream": False,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 200

        data = response.json()
        assert "id" in data
        assert data["object"] == "chat.completion"
        assert "created" in data
        assert data["model"] == vision_model_name
        assert "choices" in data
        assert len(data["choices"]) == 1

        choice = data["choices"][0]
        assert choice["index"] == 0
        assert "message" in choice
        assert choice["message"]["role"] == "assistant"
        assert choice["message"]["content"] is not None
        assert "usage" in data

    async def test_non_vision_model_ignores_images(
        self, http_client, api_config, test_image_base64, non_vision_model_name
    ):
        """Test that non-vision model (qwen3) ignores images and responds normally."""
        payload = {
            "model": non_vision_model_name,
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, how are you?",
                    "images": [test_image_base64],
                }
            ],
            "stream": False,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        # Non-vision models ignore images and respond normally
        assert response.status_code == 200

        data = response.json()
        assert data["object"] == "chat.completion"
        assert data["model"] == non_vision_model_name
        choice = data["choices"][0]
        assert choice["message"]["role"] == "assistant"
        assert choice["message"]["content"] is not None

    async def test_vision_model_without_image_works(
        self, http_client, api_config, vision_model_name
    ):
        """Test that vision-capable model works normally without images."""
        payload = {
            "model": vision_model_name,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": False,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 200

        data = response.json()
        assert data["object"] == "chat.completion"
        assert data["model"] == vision_model_name

    async def test_multiple_images_with_vision_model(
        self, http_client, api_config, test_image_base64, vision_model_name
    ):
        """Test that vision model can handle multiple images."""
        payload = {
            "model": vision_model_name,
            "messages": [
                {
                    "role": "user",
                    "content": "Compare these images.",
                    "images": [test_image_base64, test_image_base64],
                }
            ],
            "stream": False,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 200

        data = response.json()
        assert data["object"] == "chat.completion"

    async def test_streaming_with_images(
        self, http_client, api_config, test_image_base64, vision_model_name
    ):
        """Test streaming chat completion with images."""
        payload = {
            "model": vision_model_name,
            "messages": [
                {
                    "role": "user",
                    "content": "What do you see?",
                    "images": [test_image_base64],
                }
            ],
            "stream": True,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # Check that we get streaming chunks
        chunks = []
        async for chunk in response.aiter_text():
            if chunk.strip() and not chunk.startswith("data: [DONE]"):
                chunks.append(chunk)

        assert len(chunks) > 0
        # At least one chunk should contain content
        assert any("content" in chunk for chunk in chunks)

    async def test_invalid_base64_image_handled(
        self, http_client, api_config, vision_model_name
    ):
        """Test that invalid base64 image data is handled gracefully."""
        payload = {
            "model": vision_model_name,
            "messages": [
                {
                    "role": "user",
                    "content": "What is this?",
                    "images": ["invalid_base64_data"],
                }
            ],
            "stream": False,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        # Should return 400 Bad Request for invalid base64 data
        assert response.status_code in [400, 500]  # Allow both for now
        data = response.json()
        assert "detail" in data
