import pytest

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


class TestGenerate:
    """Test basic generation functionality."""

    async def test_basic_completion(self, http_client, api_config):
        """Test basic chat completion without streaming."""
        payload = {
            "model": api_config["model_name"],
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
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
        assert data["model"] == api_config["model_name"]
        assert "choices" in data
        assert len(data["choices"]) == 1

        choice = data["choices"][0]
        assert choice["index"] == 0
        assert "message" in choice
        assert choice["message"]["role"] == "assistant"
        assert choice["message"]["content"] is not None
        assert "usage" in data

    async def test_completion_with_system_message(self, http_client, api_config):
        """Test chat completion with system message."""
        payload = {
            "model": api_config["model_name"],
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2+2?"},
            ],
            "stream": False,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 200

        data = response.json()
        assert data["object"] == "chat.completion"
        assert len(data["choices"]) == 1

    async def test_multi_turn_conversation(self, http_client, api_config):
        """Test multi-turn conversation."""
        payload = {
            "model": api_config["model_name"],
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there! How can I help you?"},
                {"role": "user", "content": "Tell me about Python"},
            ],
            "stream": False,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 200

        data = response.json()
        assert data["object"] == "chat.completion"

    async def test_completion_with_parameters(self, http_client, api_config):
        """Test chat completion with generation parameters."""
        payload = {
            "model": api_config["model_name"],
            "messages": [{"role": "user", "content": "Write a short poem"}],
            "stream": False,
            "temperature": 0.8,
            "top_p": 0.9,
            "max_tokens": 50,
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 200

        data = response.json()
        assert data["object"] == "chat.completion"
