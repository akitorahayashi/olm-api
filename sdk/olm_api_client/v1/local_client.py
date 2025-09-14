from typing import AsyncGenerator, Union

import ollama


class OlmLocalClientV1:
    """
    A client for interacting with a local `ollama serve` instance using v1 API schema.

    This client converts the project's v1 API schema to direct Ollama calls,
    bypassing the proxy server while maintaining the same interface.
    """

    def __init__(self, host: str = "http://localhost:11434"):
        self.client = ollama.AsyncClient(host=host)

    async def generate(
        self, prompt: str, model_name: str, stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Generate text using local Ollama with v1 schema.

        Args:
            prompt: The prompt to send to the model.
            model_name: The name of the model to use for generation.
            stream: Whether to stream the response.

        Returns:
            Complete text response (if stream=False) or AsyncGenerator (if stream=True).
        """
        messages = [{"role": "user", "content": prompt}]

        if stream:
            return self._stream_generate(messages, model_name)
        else:
            return await self._batch_generate(messages, model_name)

    async def _stream_generate(
        self, messages, model_name: str
    ) -> AsyncGenerator[str, None]:
        """Generate text with streaming from local Ollama."""
        stream = await self.client.chat(
            model=model_name, messages=messages, stream=True
        )
        async for chunk in stream:
            if content := chunk["message"]["content"]:
                yield content

    async def _batch_generate(self, messages, model_name: str) -> str:
        """Generate complete text response from local Ollama."""
        response = await self.client.chat(
            model=model_name, messages=messages, stream=False
        )
        return response["message"]["content"]
