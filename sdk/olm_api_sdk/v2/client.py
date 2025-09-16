import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import httpx

logger = logging.getLogger(__name__)


class OlmApiClientV2:
    """
    A client for interacting with the Olm API v2.

    Provides chat completion functionality with support for:
    - Conversation history via messages array
    - System prompts and multi-role conversations
    - Tool calling and function execution
    - Fine-grained generation parameters
    - Streaming and non-streaming responses
    """

    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")
        self.chat_endpoint = f"{self.api_url}/api/v2/chat"

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        model_name: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Generate chat completion using the v2 API.

        Args:
            messages: List of message dictionaries with role, content, and optional images.
            model_name: The name of the model to use for generation.
            tools: Optional list of tool definitions for function calling.
            stream: Whether to stream the response.
            **kwargs: Additional generation parameters (temperature, top_p, etc.).

        Returns:
            Complete response dict (if stream=False) or AsyncGenerator (if stream=True).

        Examples:
            Basic usage:
                >>> client = OlmApiClientV2("http://localhost:8000")
                >>> messages = [{"role": "user", "content": "Hello!"}]
                >>> response = await client.generate(messages, "llama3.2")
                >>> print(response["choices"][0]["message"]["content"])

            With conversation history:
                >>> messages = [
                ...     {"role": "system", "content": "You are a helpful assistant."},
                ...     {"role": "user", "content": "What is Python?"},
                ...     {"role": "assistant", "content": "Python is a programming language."},
                ...     {"role": "user", "content": "What are its advantages?"}
                ... ]
                >>> response = await client.generate(messages, "llama3.2")

            With streaming:
                >>> stream = await client.generate(
                ...     messages, "llama3.2", stream=True
                ... )
                >>> async for chunk in stream:
                ...     print(chunk, end="")

            With tools:
                >>> tools = [{
                ...     "type": "function",
                ...     "function": {
                ...         "name": "get_weather",
                ...         "description": "Get weather information",
                ...         "parameters": {
                ...             "type": "object",
                ...             "properties": {
                ...                 "location": {"type": "string"}
                ...             }
                ...         }
                ...     }
                ... }]
                >>> response = await client.generate(
                ...     messages, "llama3.2", tools=tools
                ... )

            With images (vision models):
                >>> import base64
                >>> with open("image.png", "rb") as f:
                ...     image_data = base64.b64encode(f.read()).decode()
                >>> messages = [{
                ...     "role": "user",
                ...     "content": "What do you see in this image?",
                ...     "images": [image_data]
                ... }]
                >>> response = await client.generate(messages, "gemma3:4b")
        """
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
        }

        # Add optional parameters
        if tools:
            payload["tools"] = tools

        # Add generation parameters
        for key, value in kwargs.items():
            if value is not None:
                payload[key] = value

        if stream:
            return self._chat_stream_response(payload)
        else:
            return await self._chat_non_stream_response(payload)

    async def _chat_stream_response(
        self, payload: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream response from the v2 chat completions API.

        Returns complete JSON chunks to enable thought/answer distinction:
        - When delta.tool_calls exists: thought mode (save_thought function)
        - When delta.content exists: answer mode (direct response)
        """
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, read=120.0)
            ) as client:
                async with client.stream(
                    "POST",
                    self.chat_endpoint,
                    json=payload,
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                # Return the complete JSON chunk for proper thought/answer handling
                                yield data
                            except json.JSONDecodeError:
                                logger.debug(
                                    f"Failed to decode JSON from SSE line: {data_str}"
                                )
                                continue
        except httpx.RequestError:
            logger.exception("Chat completions API v2 streaming request failed")
            raise
        except Exception:
            logger.exception("Unexpected error in chat completions API v2 streaming")
            raise

    async def _chat_non_stream_response(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get non-streaming response from the v2 chat completions API.
        """
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, read=120.0)
            ) as client:
                response = await client.post(
                    self.chat_endpoint,
                    json=payload,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError:
            logger.exception("Chat completions API v2 non-streaming request failed")
            raise
        except Exception:
            logger.exception(
                "Unexpected error in chat completions API v2 non-streaming"
            )
            raise
