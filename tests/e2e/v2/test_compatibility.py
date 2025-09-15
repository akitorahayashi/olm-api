import pytest

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


class TestGenerate:
    """Test generation compatibility."""

    async def test_compatible_response_structure(self, http_client, api_config):
        """Test that response structure matches expected format."""
        payload = {
            "model": api_config["model_name"],
            "messages": [{"role": "user", "content": "Hello"}],
        }

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        data = response.json()

        # Check all required fields are present
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
