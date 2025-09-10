import asyncio
import os
import re
from typing import AsyncGenerator, Callable, Mapping, Sequence

# Default streaming configuration
DEFAULT_TOKEN_DELAY = 0.01  # Faster delay between tokens (seconds) - reduced from 0.07

DEFAULT_RESPONSES = [
    "Hello! How can I help you today?",
    "That's an interesting question. Could you tell me more about it?",
    "I understand. Is there anything else you'd like to know?",
    "Yes, I think you're absolutely right about that.",
    "I'm sorry, but could you be more specific about what you're looking for?",
]


class MockOllamaApiClient:
    """
    A high-fidelity mock client that simulates real Ollama API behavior.
    """

    def __init__(
        self,
        api_url: str | None = None,
        token_delay: float | None = None,
        responses: Mapping[str, str] | Sequence[str] | Callable | None = None,
    ):
        # Configure token delay from parameter, environment variable, or default
        if token_delay is not None:
            self.token_delay = token_delay
        else:
            env_delay = os.getenv("MOCK_TOKEN_DELAY")
            self.token_delay = (
                float(env_delay) if env_delay is not None else DEFAULT_TOKEN_DELAY
            )

        # Handle different types of responses
        if isinstance(responses, Mapping):
            self.responses_map = responses
            self.default_responses = DEFAULT_RESPONSES.copy()
            self.default_response_index = 0
        elif callable(responses):
            self.response_generator = responses
        else:
            # Handle sequence or None, maintaining original behavior
            if responses is not None:
                if not responses:
                    raise ValueError("responses must be a non-empty list")
                if not all(isinstance(x, str) for x in responses):
                    raise TypeError("all responses must be str")
                self.mock_responses = list(responses)
            else:  # responses is None
                self.mock_responses = DEFAULT_RESPONSES.copy()
            self.response_index = 0

    def _tokenize_realistic(self, text: str) -> list[str]:
        """
        Tokenize text in a way that resembles real LLM tokenization.

        This splits text into tokens that include:
        - Whole words with proper spacing
        - Punctuation as separate tokens
        - Partial words/subwords occasionally
        """
        result = []
        # First split by whitespace and punctuation, keeping separators
        tokens = re.findall(r"\S+", text)

        for i, token in enumerate(tokens):
            # Add space before token (except first token)
            if i > 0:
                result.append(" ")

            # For words longer than 8 characters, occasionally split into subwords
            if len(token) > 8 and token.isalpha():
                # 20% chance to split long words
                if hash(token) % 10 < 2:  # Deterministic pseudo-random
                    mid = len(token) // 2
                    result.append(token[:mid])
                    result.append(token[mid:])
                    continue

            # Split punctuation from words, keeping ASCII/Unicode apostrophes and hyphens
            if re.search(r"[^\w\s]", token):
                parts_inner = re.findall(r"[\w''\u2010-\u2015-]+|[^\w\s]", token)
                result.extend(parts_inner)
            else:
                result.append(token)

        return result

    async def _stream_response(self, full_text: str) -> AsyncGenerator[str, None]:
        """
        Stream response token by token, simulating real Ollama API behavior.
        """
        tokens = self._tokenize_realistic(full_text)

        for token in tokens:
            await asyncio.sleep(self.token_delay)
            yield token

    async def _stream_response(self, full_text: str) -> AsyncGenerator[str, None]:
        """
        Stream response token by token, simulating real Ollama API behavior.
        """
        tokens = self._tokenize_realistic(full_text)

        for i, token in enumerate(tokens):
            await asyncio.sleep(self.token_delay)
            yield token

    def gen_stream(
        self,
        prompt: str,
        model_name: str,
    ) -> AsyncGenerator[str, None]:
        """
        Generates mock text responses with realistic streaming behavior.

        The response generation is determined by the `responses` argument
        provided during initialization:
        - If `responses` was a dictionary, it matches the prompt against the keys (exact match first, then the first substring match by insertion order; falls back to cycling default responses).
        - If `responses` was a callable, it calls the function to get the response.
        - If `responses` was a list, it cycles through the list.

        Args:
            prompt: The prompt to send to the model.
            model_name: The name of the model to use (for protocol compatibility).

        Returns:
            AsyncGenerator yielding text chunks that match real API format.
        """
        response_text = ""

        # If a response map is set, find a response matching the prompt.
        if hasattr(self, "responses_map"):
            # Exact match
            response_text = self.responses_map.get(prompt)
            if not response_text:
                # Longest substring match (case-sensitive)
                candidates = [
                    (k, v) for k, v in self.responses_map.items() if k in prompt
                ]
                if candidates:
                    key, value = max(candidates, key=lambda kv: len(kv[0]))
                    response_text = value
            # If no match is found, use a default cycling response.
            if not response_text:
                response_text = self.default_responses[
                    self.default_response_index % len(self.default_responses)
                ]
                self.default_response_index += 1

        # If a response generator function is set, use it.
        elif hasattr(self, "response_generator"):
            response_text = self.response_generator(prompt, model_name)
            if not isinstance(response_text, str):
                response_text = str(response_text)

        # Otherwise, use the original list-based cycling behavior.
        else:
            response_text = self.mock_responses[
                self.response_index % len(self.mock_responses)
            ]
            self.response_index += 1

        return self._stream_response(response_text)

    async def gen_batch(self, prompt: str, model_name: str) -> str:
        """
        Generates complete mock response at once.

        Args:
            prompt: The prompt to send to the model.
            model_name: The name of the model to use (for protocol compatibility).

        Returns:
            Complete text response.
        """
        stream = self.gen_stream(prompt, model_name)
        return "".join([chunk async for chunk in stream])
