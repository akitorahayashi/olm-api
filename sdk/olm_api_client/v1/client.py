import json
import logging
from typing import AsyncGenerator, Union

import httpx

logger = logging.getLogger(__name__)


class OlmApiClientV1:
    """
    A client for interacting with the Olm API v1.

    Provides simple prompt-based text generation using the legacy v1 API.
    Supports both streaming and non-streaming responses.
    """

    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")
        self.generate_endpoint = f"{self.api_url}/api/v1/chat"

    async def _stream_response(
        self, prompt: str, model_name: str
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from the Olm API v1.
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
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                if "response" in data:
                                    yield data["response"]
                            except json.JSONDecodeError:
                                continue
        except httpx.RequestError:
            logger.exception("Olm API v1 streaming request failed")
            raise
        except Exception:
            logger.exception("Unexpected error in Olm API v1 streaming")
            raise

    async def _non_stream_response(self, prompt: str, model_name: str) -> str:
        """
        Get non-streaming response from the Olm API v1.
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
        except httpx.RequestError:
            logger.exception("Olm API v1 non-streaming request failed")
            raise
        except Exception:
            logger.exception("Unexpected error in Olm API v1 non-streaming")
            raise

    async def generate(
        self, prompt: str, model_name: str, stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Generates text using the Olm API v1.

        Args:
            prompt: The prompt to send to the model.
            model_name: The name of the model to use for generation.
            stream: Whether to stream the response.

        Returns:
            Complete text response (if stream=False) or AsyncGenerator (if stream=True).

        Raises:
            httpx.RequestError: If a network error occurs.

        Examples:
            Non-streaming:
                >>> client = OlmApiClientV1("http://localhost:8000")
                >>> response = await client.generate("Hello", "llama3.2")
                >>> print(response)

            Streaming:
                >>> response = await client.generate("Hello", "llama3.2", stream=True)
                >>> async for chunk in response:
                ...     print(chunk, end="")
        """
        if stream:
            return self._stream_response(prompt, model_name)
        else:
            return await self._non_stream_response(prompt, model_name)
