import json
import logging
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)


class OllamaApiClient:
    """
    A client for interacting with the Ollama API.
    """

    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")
        self.generate_endpoint = f"{self.api_url}/api/v1/generate"

    async def _stream_response(
        self, prompt: str, model_name: str
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from the Ollama API.
        """
        payload = {
            "prompt": prompt,
            "model_name": model_name,
            "stream": True,
        }

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

    async def _non_stream_response(self, prompt: str, model_name: str) -> str:
        """
        Get non-streaming response from the Ollama API.
        """
        payload = {
            "prompt": prompt,
            "model_name": model_name,
            "stream": False,
        }

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

    def gen_stream(self, prompt: str, model_name: str) -> AsyncGenerator[str, None]:
        """
        Generates text using the Ollama API with streaming.

        Args:
            prompt: The prompt to send to the model.
            model_name: The name of the model to use for generation.

        Returns:
            AsyncGenerator yielding text chunks.

        Raises:
            httpx.RequestError: If a network error occurs.
        """
        return self._stream_response(prompt, model_name)

    async def gen_batch(self, prompt: str, model_name: str) -> str:
        """
        Generates complete text using the Ollama API without streaming.

        Args:
            prompt: The prompt to send to the model.
            model_name: The name of the model to use for generation.

        Returns:
            Complete text response.

        Raises:
            httpx.RequestError: If a network error occurs.
        """
        return await self._non_stream_response(prompt, model_name)
