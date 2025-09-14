from typing import AsyncGenerator, Protocol, Union, runtime_checkable


@runtime_checkable
class OlmClientV1Protocol(Protocol):
    """
    Protocol for Olm API v1 clients.

    Provides simple prompt-based text generation with the legacy v1 API.
    """

    async def generate(
        self, prompt: str, model_name: str, stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Generate text using the model (v1 API).

        Args:
            prompt: The prompt to send to the model.
            model_name: The name of the model to use for generation.
            stream: Whether to stream the response.

        Returns:
            Complete text response (if stream=False) or AsyncGenerator (if stream=True).
        """
        ...
