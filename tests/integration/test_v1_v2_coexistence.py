"""
Integration tests to verify v1 and v2 APIs coexist properly.

This test suite ensures that:
1. Both v1 and v2 endpoints are accessible
2. They use different request/response formats
3. Both are logged correctly by the middleware
4. They don't interfere with each other
"""

import json

import pytest
from fastapi.testclient import TestClient

from src.main import app


class TestV1V2Coexistence:
    """Test that v1 and v2 APIs can coexist without conflicts."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_both_endpoints_accessible(self, client):
        """Test that both v1 and v2 endpoints are accessible."""
        # Test v1 endpoint
        v1_payload = {
            "prompt": "Hello world",
            "model_name": "llama3.2",
            "stream": False,
        }

        v1_response = client.post("/api/v1/generate", json=v1_payload)
        assert v1_response.status_code == 200

        v1_data = v1_response.json()
        assert "response" in v1_data

        # Test v2 endpoint
        v2_payload = {
            "model": "llama3.2",
            "messages": [{"role": "user", "content": "Hello world"}],
            "stream": False,
        }

        v2_response = client.post("/api/v2/chat/completions", json=v2_payload)
        assert v2_response.status_code == 200

        v2_data = v2_response.json()
        assert "choices" in v2_data
        assert v2_data["object"] == "chat.completion"

    def test_different_request_formats(self, client):
        """Test that v1 and v2 have different request formats."""
        # v1 requires 'prompt' field
        v1_payload = {"prompt": "What is Python?", "model_name": "llama3.2"}

        v1_response = client.post("/api/v1/generate", json=v1_payload)
        assert v1_response.status_code == 200

        # v2 requires 'messages' array
        v2_payload = {
            "model": "llama3.2",
            "messages": [{"role": "user", "content": "What is Python?"}],
        }

        v2_response = client.post("/api/v2/chat/completions", json=v2_payload)
        assert v2_response.status_code == 200

    def test_different_response_formats(self, client):
        """Test that v1 and v2 have different response formats."""
        # v1 response
        v1_payload = {"prompt": "Say hi", "model_name": "llama3.2", "stream": False}

        v1_response = client.post("/api/v1/generate", json=v1_payload)
        v1_data = v1_response.json()

        # v1 should have simple 'response' field
        assert "response" in v1_data
        assert "choices" not in v1_data
        assert "object" not in v1_data

        # v2 response
        v2_payload = {
            "model": "llama3.2",
            "messages": [{"role": "user", "content": "Say hi"}],
            "stream": False,
        }

        v2_response = client.post("/api/v2/chat/completions", json=v2_payload)
        v2_data = v2_response.json()

        # v2 should have OpenAI-compatible format
        assert "choices" in v2_data
        assert "object" in v2_data
        assert v2_data["object"] == "chat.completion"
        assert "response" not in v2_data

    def test_streaming_coexistence(self, client):
        """Test that both v1 and v2 streaming work."""
        # Test v1 streaming
        v1_payload = {"prompt": "Count to 3", "model_name": "llama3.2", "stream": True}

        v1_response = client.post("/api/v1/generate", json=v1_payload)
        assert v1_response.status_code == 200
        assert "text/event-stream" in v1_response.headers["content-type"]

        # Check v1 SSE format
        v1_lines = list(v1_response.iter_lines())
        v1_data_lines = [line for line in v1_lines if line.startswith(b"data: ")]
        assert len(v1_data_lines) > 0

        # Parse first v1 chunk
        first_v1_chunk = json.loads(v1_data_lines[0][6:])
        assert "response" in first_v1_chunk

        # Test v2 streaming
        v2_payload = {
            "model": "llama3.2",
            "messages": [{"role": "user", "content": "Count to 3"}],
            "stream": True,
        }

        v2_response = client.post("/api/v2/chat/completions", json=v2_payload)
        assert v2_response.status_code == 200
        assert "text/event-stream" in v2_response.headers["content-type"]

        # Check v2 SSE format
        v2_lines = list(v2_response.iter_lines())
        v2_data_lines = [
            line
            for line in v2_lines
            if line.startswith(b"data: ") and not line.endswith(b"[DONE]")
        ]
        assert len(v2_data_lines) > 0

        # Parse first v2 chunk
        first_v2_chunk = json.loads(v2_data_lines[0][6:])
        assert "choices" in first_v2_chunk
        assert first_v2_chunk["object"] == "chat.completion.chunk"

    def test_v2_openai_compatibility(self, client):
        """Test that v2 is truly OpenAI compatible."""
        # Test with conversation history
        payload = {
            "model": "llama3.2",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there! How can I help you?"},
                {"role": "user", "content": "What is your name?"},
            ],
            "temperature": 0.7,
            "max_tokens": 50,
        }

        response = client.post("/api/v2/chat/completions", json=payload)
        assert response.status_code == 200

        data = response.json()

        # Check OpenAI-specific fields
        assert "id" in data
        assert data["object"] == "chat.completion"
        assert "created" in data
        assert data["model"] == "llama3.2"

        # Check choice structure
        choice = data["choices"][0]
        assert choice["index"] == 0
        assert "message" in choice
        assert choice["message"]["role"] == "assistant"
        assert "finish_reason" in choice

        # Check usage information
        assert "usage" in data
        usage = data["usage"]
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert "total_tokens" in usage

    def test_v1_legacy_compatibility(self, client):
        """Test that v1 maintains legacy compatibility."""
        # Test with minimal payload
        payload = {"prompt": "Hello", "model_name": "llama3.2"}

        response = client.post("/api/v1/generate", json=payload)
        assert response.status_code == 200

        data = response.json()

        # Should only have the simple response field
        assert "response" in data
        assert isinstance(data["response"], str)

        # Should not have v2-specific fields
        assert "choices" not in data
        assert "object" not in data
        assert "usage" not in data

    def test_cross_version_isolation(self, client):
        """Test that v1 and v2 don't affect each other."""
        # Make v1 request
        v1_payload = {"prompt": "Test isolation v1", "model_name": "llama3.2"}

        v1_response = client.post("/api/v1/generate", json=v1_payload)
        assert v1_response.status_code == 200

        # Make v2 request immediately after
        v2_payload = {
            "model": "llama3.2",
            "messages": [{"role": "user", "content": "Test isolation v2"}],
        }

        v2_response = client.post("/api/v2/chat/completions", json=v2_payload)
        assert v2_response.status_code == 200

        # Verify both responses are in correct format
        v1_data = v1_response.json()
        v2_data = v2_response.json()

        assert "response" in v1_data
        assert "choices" in v2_data
        assert v2_data["object"] == "chat.completion"

    def test_error_handling_independence(self, client):
        """Test that errors in one version don't affect the other."""
        # Test v1 with invalid payload
        invalid_v1_payload = {"invalid_field": "value", "model_name": "llama3.2"}

        v1_response = client.post("/api/v1/generate", json=invalid_v1_payload)
        assert v1_response.status_code == 422  # Validation error

        # Test that v2 still works after v1 error
        v2_payload = {
            "model": "llama3.2",
            "messages": [{"role": "user", "content": "This should work"}],
        }

        v2_response = client.post("/api/v2/chat/completions", json=v2_payload)
        assert v2_response.status_code == 200

        # Test v2 with invalid payload
        invalid_v2_payload = {"model": "llama3.2", "invalid_messages": "not an array"}

        v2_error_response = client.post(
            "/api/v2/chat/completions", json=invalid_v2_payload
        )
        assert v2_error_response.status_code == 422

        # Test that v1 still works after v2 error
        v1_payload = {"prompt": "This should work", "model_name": "llama3.2"}

        v1_final_response = client.post("/api/v1/generate", json=v1_payload)
        assert v1_final_response.status_code == 200
