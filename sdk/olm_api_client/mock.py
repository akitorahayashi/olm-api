import asyncio
import os
import re
from typing import AsyncGenerator, Callable

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
        responses: dict[str, str] | list[str] | Callable | None = None,
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
        if isinstance(responses, dict):
            self.responses_map = responses
            self.default_responses = DEFAULT_RESPONSES.copy()
            self.default_response_index = 0
        elif callable(responses):
            self.response_generator = responses
        else:
            # Handle list or None, maintaining original behavior
            if responses is not None:
                if not responses:  # Check for empty list
                    raise ValueError("responses must be a non-empty list")
                self.mock_responses = list(responses)
            else:  # responses is None
                self.mock_responses = DEFAULT_RESPONSES.copy()
            self.response_index = 0

    def _tokenize_realistic(self, text: str) -> list[str]:
        """
        Tokenize text in a way that resembles real LLM tokenization.

        This splits text into tokens that include:
        - Whole words
        - Punctuation as separate tokens
        - Partial words/subwords occasionally
        """
        result = []
        # First split by whitespace and punctuation, keeping separators
        tokens = re.findall(r"\S+|\s+", text)

        for token in tokens:
            if token.isspace():
                continue  # Skip pure whitespace tokens

            # For words longer than 8 characters, occasionally split into subwords
            if len(token) > 8 and token.isalpha():
                # 20% chance to split long words
                if hash(token) % 10 < 2:  # Deterministic pseudo-random
                    mid = len(token) // 2
                    result.append(token[:mid])
                    result.append(token[mid:])
                    continue

            # Split punctuation from words, keeping apostrophes and hyphens
            if re.search(r"[^\w\s]", token):
                parts_inner = re.findall(r"[\w'-]+|[^\w\s]", token)
                result.extend(parts_inner)
            else:
                result.append(token)

        return result

    async def _stream_response(self, full_text: str) -> AsyncGenerator[str, None]:
        """
        Stream response token by token, simulating real Ollama API behavior.
        """
        tokens = self._tokenize_realistic(full_text)

        for i, token in enumerate(tokens):
            await asyncio.sleep(self.token_delay)

            # Add space before token if it's a word-like token (not punctuation)
            if i > 0 and token[0].isalnum() and not tokens[i - 1].endswith("\n"):
                yield " "
                await asyncio.sleep(self.token_delay * 0.3)  # Shorter delay for spaces

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
        - If `responses` was a dictionary, it matches the prompt against the keys.
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
            # Check for an exact match first, then a partial match.
            response_text = self.responses_map.get(prompt)
            if not response_text:
                for key, value in self.responses_map.items():
                    if key in prompt:
                        response_text = value
                        break
            # If no match is found, use a default cycling response.
            if not response_text:
                response_text = self.default_responses[
                    self.default_response_index % len(self.default_responses)
                ]
                self.default_response_index += 1

        # If a response generator function is set, use it.
        elif hasattr(self, "response_generator"):
            response_text = self.response_generator(prompt, model_name)

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
