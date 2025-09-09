from typing import AsyncGenerator, Protocol, runtime_checkable


@runtime_checkable
class OllamaClientProtocol(Protocol):
    """
    Protocol for Ollama API clients.
    """

    def gen_stream(self, prompt: str, model_name: str) -> AsyncGenerator[str, None]:
        """
        Generate text using the model with streaming.

        Args:
            prompt: The prompt to send to the model.
            model_name: The name of the model to use for generation.

        Returns:
            AsyncGenerator yielding text chunks.
        """
        ...

    async def gen_batch(self, prompt: str, model_name: str) -> str:
        """
        Generate complete text using the model without streaming.

        Args:
            prompt: The prompt to send to the model.
            model_name: The name of the model to use for generation.

        Returns:
            Complete text response.
        """
        ...
