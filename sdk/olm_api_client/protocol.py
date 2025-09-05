from typing import AsyncGenerator, Protocol, runtime_checkable


@runtime_checkable
class OllamaClientProtocol(Protocol):
    """
    Protocol for Ollama API clients.
    """

    def gen_stream(
        self, prompt: str, model: str | None = None, think: bool | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate text using the model with streaming.

        Args:
            prompt: The prompt to send to the model.
            model: The name of the model to use for generation.
            think: Whether to enable thinking mode. If None, uses model default.

        Returns:
            AsyncGenerator yielding text chunks.
        """
        ...

    async def gen_batch(
        self, prompt: str, model: str | None = None, think: bool | None = None
    ) -> str:
        """
        Generate complete text using the model without streaming.

        Args:
            prompt: The prompt to send to the model.
            model: The name of the model to use for generation.
            think: Whether to enable thinking mode. If None, uses model default.

        Returns:
            Complete text response.
        """
        ...
