import asyncio
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Sequence, Union

DEFAULT_TOKEN_DELAY = 0.01

DEFAULT_RESPONSES = [
    "Hello! How can I help you today?",
    "That's an interesting question. Could you tell me more about it?",
    "I understand. Is there anything else you'd like to know?",
    "Yes, I think you're absolutely right about that.",
    "I'm sorry, but could you be more specific about what you're looking for?",
]


class MockOlmClientV2:
    """
    A high-fidelity mock client that simulates v2 API behavior with OpenAI-compatible responses.
    """

    def __init__(
        self,
        api_url: str = None,
        token_delay: float = None,
        responses: Sequence[str] = None,
    ):
        # Configure token delay
        if token_delay is not None:
            self.token_delay = token_delay
        else:
            env_delay = os.getenv("MOCK_TOKEN_DELAY")
            self.token_delay = (
                float(env_delay) if env_delay is not None else DEFAULT_TOKEN_DELAY
            )

        # Handle responses
        if responses is not None:
            if not responses:
                raise ValueError("responses must be a non-empty list")
            if not all(isinstance(x, str) for x in responses):
                raise TypeError("all responses must be str")
            self.mock_responses = list(responses)
        else:
            self.mock_responses = DEFAULT_RESPONSES.copy()

        self.response_index = 0

    def _tokenize_realistic(self, text: str) -> list[str]:
        """Tokenize text in a way that resembles real LLM tokenization."""
        import re

        result = []
        tokens = re.findall(r"\S+", text)

        for i, token in enumerate(tokens):
            if i > 0:
                result.append(" ")

            if len(token) > 8 and token.isalpha():
                if hash(token) % 10 < 2:  # 20% chance to split long words
                    mid = len(token) // 2
                    result.append(token[:mid])
                    result.append(token[mid:])
                    continue

            if re.search(r"[^\w\s]", token):
                parts_inner = re.findall(r"[\w''\u2010-\u2015-]+|[^\w\s]", token)
                result.extend(parts_inner)
            else:
                result.append(token)

        return result

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        model_name: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Mock chat completion using v2 API format.

        Args:
            messages: List of message dictionaries with role and content.
            model_name: The name of the model (for protocol compatibility).
            tools: Optional list of tool definitions (ignored in mock).
            stream: Whether to stream the response.
            **kwargs: Additional generation parameters (ignored in mock).

        Returns:
            Complete response dict (if stream=False) or AsyncGenerator (if stream=True).
        """
        # Cycle through mock responses
        response_text = self.mock_responses[
            self.response_index % len(self.mock_responses)
        ]
        self.response_index += 1

        if stream:
            return self._mock_chat_stream(response_text, model_name)
        else:
            return self._create_chat_response(response_text, model_name)

    def _create_chat_response(self, content: str, model: str) -> Dict[str, Any]:
        """Create OpenAI-compatible chat response."""
        return {
            "id": f"chatcmpl-mock-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,  # Mock values
                "completion_tokens": len(content.split()),
                "total_tokens": 10 + len(content.split()),
            },
        }

    async def _mock_chat_stream(
        self, full_text: str, model: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream mock chat response in OpenAI format."""
        tokens = self._tokenize_realistic(full_text)
        created_time = int(time.time())
        created_id = f"chatcmpl-mock-{created_time}"

        # Send first chunk with role
        first_chunk = {
            "id": created_id,
            "object": "chat.completion.chunk",
            "created": created_time,
            "model": model,
            "choices": [
                {"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}
            ],
        }
        yield first_chunk

        # Send content chunks
        for token in tokens:
            chunk = {
                "id": created_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": model,
                "choices": [
                    {"index": 0, "delta": {"content": token}, "finish_reason": None}
                ],
            }
            yield chunk
            await asyncio.sleep(self.token_delay)

        # Send final chunk
        final_chunk = {
            "id": f"chatcmpl-mock-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield final_chunk
