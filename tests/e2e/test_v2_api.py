import json

import pytest
from fastapi.testclient import TestClient

from src.main import app


class TestV2ChatCompletions:
    """
    Test suite for v2 chat completions API endpoint.
    Tests both streaming and non-streaming responses.
    """

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_chat_completion_basic(self, client):
        """Test basic chat completion without streaming."""
        payload = {
            "model": "llama3.2",
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": False,
        }

        response = client.post("/api/v2/chat/completions", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "id" in data
        assert data["object"] == "chat.completion"
        assert "created" in data
        assert data["model"] == "llama3.2"
        assert "choices" in data
        assert len(data["choices"]) == 1

        choice = data["choices"][0]
        assert choice["index"] == 0
        assert "message" in choice
        assert choice["message"]["role"] == "assistant"
        assert choice["message"]["content"] is not None
        assert "usage" in data

    def test_chat_completion_with_system_message(self, client):
        """Test chat completion with system message."""
        payload = {
            "model": "llama3.2",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2+2?"},
            ],
            "stream": False,
        }

        response = client.post("/api/v2/chat/completions", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["object"] == "chat.completion"
        assert len(data["choices"]) == 1

    def test_chat_completion_conversation(self, client):
        """Test multi-turn conversation."""
        payload = {
            "model": "llama3.2",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there! How can I help you?"},
                {"role": "user", "content": "Tell me about Python"},
            ],
            "stream": False,
        }

        response = client.post("/api/v2/chat/completions", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["object"] == "chat.completion"

    def test_chat_completion_with_parameters(self, client):
        """Test chat completion with generation parameters."""
        payload = {
            "model": "llama3.2",
            "messages": [{"role": "user", "content": "Write a short poem"}],
            "stream": False,
            "temperature": 0.8,
            "top_p": 0.9,
            "max_tokens": 50,
        }

        response = client.post("/api/v2/chat/completions", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["object"] == "chat.completion"

    def test_chat_completion_streaming(self, client):
        """Test streaming chat completion."""
        payload = {
            "model": "llama3.2",
            "messages": [{"role": "user", "content": "Count from 1 to 5"}],
            "stream": True,
        }

        response = client.post("/api/v2/chat/completions", json=payload)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        chunks = []
        for line in response.iter_lines():
            if line.startswith(b"data: "):
                data_str = line[6:].decode("utf-8").strip()
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

    def test_chat_completion_with_tools(self, client):
        """Test chat completion with tool definitions."""
        payload = {
            "model": "llama3.2",
            "messages": [{"role": "user", "content": "What's the weather like?"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get current weather information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "City name",
                                }
                            },
                            "required": ["location"],
                        },
                    },
                }
            ],
            "stream": False,
        }

        response = client.post("/api/v2/chat/completions", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["object"] == "chat.completion"
        # Tool calling behavior depends on model capabilities

    def test_chat_completion_validation_errors(self, client):
        """Test validation errors for malformed requests."""
        # Missing required field: model
        payload = {"messages": [{"role": "user", "content": "Hello"}]}

        response = client.post("/api/v2/chat/completions", json=payload)
        assert response.status_code == 422

        # Empty messages array
        payload = {"model": "llama3.2", "messages": []}

        response = client.post("/api/v2/chat/completions", json=payload)
        assert response.status_code == 422

        # Invalid role
        payload = {
            "model": "llama3.2",
            "messages": [{"role": "invalid", "content": "Hello"}],
        }

        response = client.post("/api/v2/chat/completions", json=payload)
        assert response.status_code == 422

    def test_chat_completion_field_aliases(self, client):
        """Test that field aliases work correctly."""
        payload = {
            "model_name": "llama3.2",  # Use alias instead of "model"
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        }

        response = client.post("/api/v2/chat/completions", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["model"] == "llama3.2"


class TestV2Compatibility:
    """Test v2 API compatibility with OpenAI format."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_openai_compatible_response_structure(self, client):
        """Test that response structure matches OpenAI format."""
        payload = {
            "model": "llama3.2",
            "messages": [{"role": "user", "content": "Hello"}],
        }

        response = client.post("/api/v2/chat/completions", json=payload)
        data = response.json()

        # Check all required OpenAI fields are present
        required_fields = ["id", "object", "created", "model", "choices", "usage"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check choice structure
        choice = data["choices"][0]
        choice_fields = ["index", "message", "finish_reason"]
        for field in choice_fields:
            assert field in choice, f"Missing required choice field: {field}"

        # Check message structure
        message = choice["message"]
        message_fields = ["role", "content"]
        for field in message_fields:
            assert field in message, f"Missing required message field: {field}"

        # Check usage structure
        usage = data["usage"]
        usage_fields = ["prompt_tokens", "completion_tokens", "total_tokens"]
        for field in usage_fields:
            assert field in usage, f"Missing required usage field: {field}"
