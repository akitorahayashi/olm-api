import asyncio
import os
from typing import Any, AsyncGenerator, Dict, Optional, Sequence, Union

DEFAULT_TOKEN_DELAY = 0.01

DEFAULT_RESPONSES = [
    "Hello! How can I help you today?",
    "That's an interesting question. Could you tell me more about it?",
    "I understand. Is there anything else you'd like to know?",
    "Yes, I think you're absolutely right about that.",
    "I'm sorry, but could you be more specific about what you're looking for?",
]


class MockOlmClientV1:
    """
    A high-fidelity mock client that simulates v1 API behavior.
    """

    def __init__(
        self,
        api_url: str = None,
        token_delay: float = None,
        responses: Union[Dict[str, str], Sequence[str]] = None,
    ):
        # Configure token delay
        if token_delay is not None:
            self.token_delay = token_delay
        else:
            env_delay = os.getenv("MOCK_TOKEN_DELAY")
            try:
                self.token_delay = (
                    float(env_delay) if env_delay is not None else DEFAULT_TOKEN_DELAY
                )
            except ValueError:
                self.token_delay = DEFAULT_TOKEN_DELAY

        # Handle responses
        self.keyed_responses: Dict[str, str] = {}
        self.fallback_responses: Sequence[str] = DEFAULT_RESPONSES.copy()
        self.response_index = 0

        if responses is not None:
            if isinstance(responses, dict):
                if not all(
                    isinstance(k, str) and isinstance(v, str)
                    for k, v in responses.items()
                ):
                    raise TypeError(
                        "All keys and values in the responses dictionary must be strings."
                    )
                self.keyed_responses = responses
            elif isinstance(responses, (list, tuple)):
                if not responses:
                    raise ValueError("The responses sequence cannot be empty.")
                if not all(isinstance(x, str) for x in responses):
                    raise TypeError(
                        "All items in the responses sequence must be strings."
                    )
                self.fallback_responses = list(responses)
            else:
                raise TypeError(
                    "The 'responses' argument must be a dictionary or a sequence of strings."
                )

    def _tokenize_realistic(self, text: str) -> list[str]:
        """Tokenize text in a way that resembles real LLM tokenization."""
        import re

        result = []
        tokens = re.findall(r"\S+", text)

        for i, token in enumerate(tokens):
            if i > 0:
                result.append(" ")

            if len(token) > 8 and token.isalpha():
                import hashlib

                # 安定ハッシュ（先頭2バイト）で 20% 判定
                h = int(
                    hashlib.blake2s(token.encode("utf-8"), digest_size=2).hexdigest(),
                    16,
                )
                if h % 10 < 2:
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

    async def _stream_response(
        self, full_text: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response token by token with structured format."""
        tokens = self._tokenize_realistic(full_text)
        accumulated_content = ""

        for token in tokens:
            accumulated_content += token

            # Mock structured response format
            yield {
                "think": "Mock thinking process",
                "content": accumulated_content,
                "full_response": accumulated_content,
            }
            await asyncio.sleep(self.token_delay)

    async def generate(
        self,
        prompt: str,
        model_name: str,
        stream: bool = False,
        think: Optional[bool] = None,
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Mock generate text using v1 API format.

        Args:
            prompt: The prompt to send to the model.
            model_name: The name of the model (for protocol compatibility).
            stream: Whether to stream the response.
            think: Whether to enable thinking mode (for protocol compatibility).

        Returns:
            Complete JSON response (if stream=False) or AsyncGenerator of JSON chunks (if stream=True).
            Each response contains 'think', 'content', and 'response' fields.
        """
        # Unused args kept for protocol compatibility
        del model_name, think

        # Check for a keyed response, otherwise use a cycling fallback
        if prompt in self.keyed_responses:
            response_text = self.keyed_responses[prompt]
        else:
            response_text = self.fallback_responses[
                self.response_index % len(self.fallback_responses)
            ]
            self.response_index += 1

        if stream:
            return self._stream_response(response_text)
        else:
            # Simulate async operation
            await asyncio.sleep(0.001)
            return {
                "think": "Mock thinking process",
                "content": response_text,
                "full_response": response_text,
            }
