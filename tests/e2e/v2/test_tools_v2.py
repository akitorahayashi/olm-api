import pytest

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


class TestGenerate:
    """Test generation with tool calling functionality."""

    async def test_completion_with_tools(self, http_client, api_config):
        """Test chat completion with tool definitions."""
        payload = {
            "model": api_config["model_name"],
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

        response = await http_client.post(
            api_config["v2_chat_completions_url"], json=payload
        )
        assert response.status_code == 200

        data = response.json()
        assert data["object"] == "chat.completion"
        # Tool calling behavior depends on model capabilities
