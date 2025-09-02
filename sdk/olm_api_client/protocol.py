from typing import AsyncGenerator, Protocol, runtime_checkable


@runtime_checkable
class OllamaClientProtocol(Protocol):
    """
    Protocol for Ollama API clients.
    """

    def generate(
        self, prompt: str, model: str | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate text using the model with streaming.

        Args:
            prompt: The prompt to send to the model.
            model: The name of the model to use for generation.

        Returns:
            AsyncGenerator yielding text chunks.
        """
        ...
