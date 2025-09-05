import json
import logging
import os
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)


class OllamaApiClient:
    """
    A client for interacting with the Ollama API.
    """

    def __init__(self, api_url: str | None = None):
        self.api_url = api_url or os.getenv("OLM_API_ENDPOINT")
        if not self.api_url:
            raise ValueError(
                "API URL must be provided either as parameter or OLM_API_ENDPOINT environment variable"
            )
        self.api_url = self.api_url.rstrip("/")
        self.generate_endpoint = f"{self.api_url}/api/v1/generate"

    async def _stream_response(
        self, prompt: str, model: str, think: bool | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from the Ollama API.
        """
        payload = {
            "prompt": prompt,
            "model_name": model,
            "stream": True,
        }
        if think is not None:
            payload["think"] = think

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, read=120.0)
            ) as client:
                async with client.stream(
                    "POST",
                    self.generate_endpoint,
                    json=payload,
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])  # Remove "data: " prefix
                                if "response" in data:
                                    yield data["response"]
                            except json.JSONDecodeError:
                                continue
        except httpx.RequestError as e:
            logger.error(f"Ollama API streaming request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Ollama API streaming: {e}")
            raise

    async def _non_stream_response(
        self, prompt: str, model: str, think: bool | None = None
    ) -> str:
        """
        Get non-streaming response from the Ollama API.
        """
        payload = {
            "prompt": prompt,
            "model_name": model,
            "stream": False,
        }
        if think is not None:
            payload["think"] = think

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, read=120.0)
            ) as client:
                response = await client.post(
                    self.generate_endpoint,
                    json=payload,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()

                data = response.json()
                return data.get("response", "")
        except httpx.RequestError as e:
            logger.error(f"Ollama API non-streaming request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Ollama API non-streaming: {e}")
            raise

    def gen_stream(
        self, prompt: str, model: str | None = None, think: bool | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Generates text using the Ollama API with streaming.

        Args:
            prompt: The prompt to send to the model.
            model: The name of the model to use for generation.
            think: Whether to enable thinking mode. If None, uses model default.

        Returns:
            AsyncGenerator yielding text chunks.

        Raises:
            httpx.RequestError: If a network error occurs.
        """
        # Use environment variable model if not specified
        if model is None:
            model = os.getenv("OLLAMA_MODEL")
            if not model:
                raise ValueError(
                    "OLLAMA_MODEL is not configured in environment variables."
                )

        return self._stream_response(prompt, model, think)

    async def gen_batch(
        self, prompt: str, model: str | None = None, think: bool | None = None
    ) -> str:
        """
        Generates complete text using the Ollama API without streaming.

        Args:
            prompt: The prompt to send to the model.
            model: The name of the model to use for generation.
            think: Whether to enable thinking mode. If None, uses model default.

        Returns:
            Complete text response.

        Raises:
            httpx.RequestError: If a network error occurs.
        """
        # Use environment variable model if not specified
        if model is None:
            model = os.getenv("OLLAMA_MODEL")
            if not model:
                raise ValueError(
                    "OLLAMA_MODEL is not configured in environment variables."
                )

        return await self._non_stream_response(prompt, model, think)
