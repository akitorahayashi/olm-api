import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional, Union

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

    def _build_payload(
        self,
        prompt: str,
        model_name: str,
        stream: bool = False,
        think: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Helper to build the request payload."""
        payload = {
            "prompt": prompt,
            "model_name": model_name,
            "stream": stream,
        }
        if think is not None:
            payload["think"] = think
        return payload

    async def _stream_response(
        self, prompt: str, model_name: str, think: Optional[bool] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream response from the Olm API v1.
        """
        payload = self._build_payload(prompt, model_name, stream=True, think=think)

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
                                    yield data
                            except json.JSONDecodeError:
                                continue
        except httpx.RequestError:
            logger.exception("Olm API v1 streaming request failed")
            raise
        except Exception:
            logger.exception("Unexpected error in Olm API v1 streaming")
            raise

    async def _non_stream_response(
        self, prompt: str, model_name: str, think: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Get non-streaming response from the Olm API v1.
        """
        payload = self._build_payload(prompt, model_name, stream=False, think=think)

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
                return data
        except httpx.RequestError:
            logger.exception("Olm API v1 non-streaming request failed")
            raise
        except Exception:
            logger.exception("Unexpected error in Olm API v1 non-streaming")
            raise

    async def generate(
        self,
        prompt: str,
        model_name: str,
        stream: bool = False,
        think: Optional[bool] = None,
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Generates text using the Olm API v1.

        Args:
            prompt: The prompt to send to the model.
            model_name: The name of the model to use for generation.
            stream: Whether to stream the response.
            think: Whether to enable thinking mode.

        Returns:
            Complete JSON response (if stream=False) or AsyncGenerator of JSON chunks (if stream=True).
            Each response contains 'think', 'content', and 'response' fields.

        Raises:
            httpx.RequestError: If a network error occurs.

        Examples:
            Non-streaming:
                >>> client = OlmApiClientV1("http://localhost:8000")
                >>> response = await client.generate("Hello", "llama3.2", think=True)
                >>> print(f"Thinking: {response['think']}")
                >>> print(f"Content: {response['content']}")

            Streaming:
                >>> response = await client.generate("Hello", "llama3.2", stream=True, think=True)
                >>> async for chunk in response:
                ...     print(f"Content: {chunk['content']}", end="")
        """
        if stream:
            return self._stream_response(prompt, model_name, think)
        else:
            return await self._non_stream_response(prompt, model_name, think)

    def _non_stream_response_sync(
        self, prompt: str, model_name: str, think: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Get non-streaming response from the Olm API v1 (Synchronous).
        """
        payload = self._build_payload(prompt, model_name, stream=False, think=think)

        try:
            with httpx.Client(timeout=httpx.Timeout(10.0, read=120.0)) as client:
                response = client.post(
                    self.generate_endpoint,
                    json=payload,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
                return data
        except httpx.RequestError:
            logger.exception("Olm API v1 non-streaming sync request failed")
            raise
        except Exception:
            logger.exception("Unexpected error in Olm API v1 non-streaming sync")
            raise

    def generate_sync(
        self,
        prompt: str,
        model_name: str,
        think: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Generate text using the Olm API v1 (Synchronous version).

        Args:
            prompt: The prompt to send to the model.
            model_name: The name of the model to use for generation.
            think: Whether to enable thinking mode.

        Returns:
            Complete JSON response. Streaming is not supported in sync version.
            Response contains 'think', 'content', and 'response' fields.

        Raises:
            httpx.RequestError: If a network error occurs.

        Examples:
            >>> client = OlmApiClientV1("http://localhost:8000")
            >>> response = client.generate_sync("Hello", "llama3.2", think=True)
            >>> print(f"Thinking: {response['think']}")
            >>> print(f"Content: {response['content']}")
        """
        return self._non_stream_response_sync(prompt, model_name, think)
