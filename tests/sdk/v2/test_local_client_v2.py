import json
from unittest.mock import AsyncMock, patch

import pytest

from sdk.olm_api_client.v2.local_client import OlmLocalClientV2
from sdk.olm_api_client.v2.protocol import OlmClientV2Protocol


class TestOlmLocalClientV2:
    """Test cases for OlmLocalClientV2"""

    def test_implements_protocol(self):
        """Test that OlmLocalClientV2 implements OlmClientV2Protocol"""
        client = OlmLocalClientV2()
        assert isinstance(client, OlmClientV2Protocol)

    @pytest.mark.asyncio
    async def test_generate_non_streaming(self):
        """Test non-streaming chat completion"""
        with patch(
            "sdk.olm_api_client.v2.local_client.ollama.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock Ollama response
            mock_ollama_response = {
                "message": {"role": "assistant", "content": "Hello, world!"},
                "prompt_eval_count": 10,
                "eval_count": 5,
            }
            mock_client.chat.return_value = mock_ollama_response

            client = OlmLocalClientV2()
            messages = [{"role": "user", "content": "Hello"}]

            result = await client.generate(messages, "qwen3:0.6b", stream=False)

            # Verify OpenAI-compatible format
            assert result["id"].startswith("chatcmpl-local-")
            assert result["object"] == "chat.completion"
            assert result["model"] == "qwen3:0.6b"
            assert result["choices"][0]["message"]["role"] == "assistant"
            assert result["choices"][0]["message"]["content"] == "Hello, world!"
            assert result["usage"]["prompt_tokens"] == 10
            assert result["usage"]["completion_tokens"] == 5
            assert result["usage"]["total_tokens"] == 15

    @pytest.mark.asyncio
    async def test_generate_streaming(self):
        """Test streaming chat completion returns OpenAI-compatible JSON chunks"""
        with patch(
            "sdk.olm_api_client.v2.local_client.ollama.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock streaming response from ollama
            async def mock_stream():
                yield {
                    "model": "qwen3:0.6b",
                    "created_at": "2023-12-19T20:54:00.123Z",
                    "message": {"role": "assistant", "content": "Hello"},
                    "done": False,
                }
                yield {
                    "model": "qwen3:0.6b",
                    "created_at": "2023-12-19T20:54:00.223Z",
                    "message": {"role": "assistant", "content": " world"},
                    "done": False,
                }
                yield {
                    "model": "qwen3:0.6b",
                    "created_at": "2023-12-19T20:54:00.323Z",
                    "message": {"role": "assistant", "content": "!"},
                    "done": True,
                    "total_duration": 12345,
                    "prompt_eval_count": 10,
                    "eval_count": 5,
                }

            mock_client.chat.return_value = mock_stream()

            client = OlmLocalClientV2()
            messages = [{"role": "user", "content": "Hello"}]

            result_generator = await client.generate(
                messages, "qwen3:0.6b", stream=True
            )

            chunks = []
            async for chunk_str in result_generator:
                chunks.append(chunk_str)

            assert len(chunks) == 3

            # Verify that each chunk is a JSON string in the correct format
            for i, chunk_str in enumerate(chunks):
                assert isinstance(chunk_str, str)
                chunk = json.loads(chunk_str)
                assert "id" in chunk
                assert chunk["object"] == "chat.completion.chunk"
                assert chunk["model"] == "qwen3:0.6b"
                assert "choices" in chunk
                assert len(chunk["choices"]) == 1
                delta = chunk["choices"][0]["delta"]
                assert "content" in delta

            # Check content
            assert json.loads(chunks[0])["choices"][0]["delta"]["content"] == "Hello"
            assert json.loads(chunks[1])["choices"][0]["delta"]["content"] == " world"
            assert json.loads(chunks[2])["choices"][0]["delta"]["content"] == "!"

    @pytest.mark.asyncio
    async def test_generate_with_tools(self):
        """Test chat completion with tools"""
        with patch(
            "sdk.olm_api_client.v2.local_client.ollama.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock Ollama response with tool calls
            mock_ollama_response = {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "save_thought",
                                "arguments": '{"thought_content": "Thinking about the problem..."}',
                            },
                        }
                    ],
                },
                "prompt_eval_count": 15,
                "eval_count": 8,
            }
            mock_client.chat.return_value = mock_ollama_response

            client = OlmLocalClientV2()
            messages = [{"role": "user", "content": "Think about this"}]
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "save_thought",
                        "description": "Save a thought",
                        "parameters": {
                            "type": "object",
                            "properties": {"thought_content": {"type": "string"}},
                        },
                    },
                }
            ]

            result = await client.generate(
                messages, "qwen3:0.6b", tools=tools, stream=False
            )

            # Verify OpenAI-compatible format with tool calls
            assert result["choices"][0]["message"]["content"] is None
            assert result["choices"][0]["message"]["tool_calls"] is not None
            assert len(result["choices"][0]["message"]["tool_calls"]) == 1
            assert (
                result["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
                == "save_thought"
            )
