from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import ollama
from src.utils.thinking_parser import parse_thinking_response


class OlmLocalClientV2:
    """
    A client for interacting with a local `ollama serve` instance using v2 API schema.

    This client converts the project's v2 API schema to direct Ollama calls,
    bypassing the proxy server while maintaining the same interface.
    """

    def __init__(self, host: str = "http://localhost:11434"):
        self.client = ollama.AsyncClient(host=host)

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        model_name: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """
        Generate chat completion using local Ollama with v2 schema.

        Args:
            messages: List of message dictionaries with role and content.
            model_name: The name of the model to use for generation.
            tools: Optional list of tool definitions for function calling.
            stream: Whether to stream the response.
            **kwargs: Additional generation parameters (temperature, top_p, etc.).

        Returns:
            Complete response dict (if stream=False) or AsyncGenerator (if stream=True).
        """
        # Build parameters for ollama.chat call
        chat_params = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
        }

        # Add tools if provided
        if tools:
            chat_params["tools"] = tools

        # Add generation parameters
        if kwargs:
            chat_params["options"] = kwargs

        if stream:
            return self._stream_generate(**chat_params)
        else:
            return await self._batch_generate(**chat_params)

    async def _stream_generate(self, **chat_params) -> AsyncGenerator[str, None]:
        """Generate JSON chunks from local Ollama streaming with thinking separation."""
        import json
        import time

        stream = await self.client.chat(**chat_params)
        model = chat_params.get("model", "unknown")

        async for chunk in stream:
            if content := chunk["message"]["content"]:
                # For streaming, we want to send the incremental content, not accumulated
                # Parse just this chunk to determine if it's thinking or content
                parsed = parse_thinking_response(content)

                # Convert to streaming format with incremental content
                chunk_data = {
                    "id": f"chatcmpl-local-{int(time.time())}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": content,  # Send incremental content
                                "think": parsed["thinking"],  # Custom field
                                "response": content,  # Custom field - same as content for streaming
                            },
                            "finish_reason": None,
                        }
                    ],
                }
                yield json.dumps(chunk_data)

    async def _batch_generate(self, **chat_params) -> Dict[str, Any]:
        """Generate complete response from local Ollama and convert to chat completion format."""
        chat_params["stream"] = False
        ollama_response = await self.client.chat(**chat_params)

        # Transform to chat completion format
        return self._transform_to_chat_format(ollama_response, chat_params["model"])

    def _transform_to_chat_format(
        self, ollama_response: Dict[str, Any], model: str
    ) -> Dict[str, Any]:
        """Transform Ollama response to chat completion format with thinking separation."""
        message = ollama_response.get("message", {})
        raw_content = message.get("content", "")

        # Parse thinking vs content using same logic as API server
        parsed = parse_thinking_response(raw_content)

        # Handle tool calls if present
        tool_calls = message.get("tool_calls")

        return {
            "id": f"chatcmpl-local-{hash(str(ollama_response))}",
            "object": "chat.completion",
            "created": 1000000000,  # Mock timestamp
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": message.get("role", "assistant"),
                        "content": (
                            parsed["content"] if not tool_calls else None
                        ),  # Clean content without think tags, None if tool calls
                        "think": parsed["thinking"],  # Custom field for thinking
                        "response": raw_content,  # Custom field for raw response
                        "tool_calls": tool_calls,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": ollama_response.get("prompt_eval_count", 0),
                "completion_tokens": ollama_response.get("eval_count", 0),
                "total_tokens": ollama_response.get("prompt_eval_count", 0)
                + ollama_response.get("eval_count", 0),
            },
        }
