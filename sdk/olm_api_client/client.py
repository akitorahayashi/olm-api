import json
import logging
import os
from typing import AsyncGenerator

import httpx
import streamlit as st

logger = logging.getLogger(__name__)


class OllamaApiClient:
    """
    A client for interacting with the Ollama API.
    """

    def __init__(self):
        self.api_url = os.getenv("OLLAMA_API_ENDPOINT")
        if not self.api_url:
            # Fallback to Streamlit secrets if available
            try:
                self.api_url = st.secrets.get("OLLAMA_API_ENDPOINT")
            except Exception:
                pass

        if not self.api_url:
            raise ValueError(
                "OLLAMA_API_ENDPOINT is not configured in environment variables or Streamlit secrets."
            )
        self.generate_endpoint = f"{self.api_url}/api/v1/generate"

    async def _stream_response(
        self, prompt: str, model: str
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from the Ollama API.
        """
        payload = {
            "prompt": prompt,
            "model_name": model,
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

    def generate(self, prompt: str, model: str = None) -> AsyncGenerator[str, None]:
        """
        Generates text using the Ollama API with streaming.

        Args:
            prompt: The prompt to send to the model.
            model: The name of the model to use for generation.

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

        return self._stream_response(prompt, model)
