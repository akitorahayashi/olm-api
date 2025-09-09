from typing import AsyncGenerator

import ollama


class OllamaLocalClient:
    """
    A client for interacting with a local `ollama serve` instance.
    This client uses the official `ollama` Python library.
    """

    def __init__(self, host: str = "http://localhost:11434"):
        self.client = ollama.AsyncClient(host=host)

    async def gen_stream(
        self, prompt: str, model_name: str
    ) -> AsyncGenerator[str, None]:
        """
        Generates text from a local Ollama instance with streaming.
        """
        messages = [{"role": "user", "content": prompt}]
        stream = await self.client.chat(
            model=model_name, messages=messages, stream=True
        )
        async for chunk in stream:
            if content := chunk["message"]["content"]:
                yield content

    async def gen_batch(self, prompt: str, model_name: str) -> str:
        """
        Generates a complete text response from a local Ollama instance.
        """
        messages = [{"role": "user", "content": prompt}]
        response = await self.client.chat(
            model=model_name, messages=messages, stream=False
        )
        return response["message"]["content"]
