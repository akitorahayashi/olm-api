from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Optional,
    Protocol,
    Union,
    runtime_checkable,
)


@runtime_checkable
class OlmClientV1Protocol(Protocol):
    """
    Protocol for Olm API v1 clients.

    Provides simple prompt-based text generation with the legacy v1 API.
    """

    async def generate(
        self,
        prompt: str,
        model_name: str,
        stream: bool = False,
        think: Optional[bool] = None,
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Generate text using the model (v1 API).

        Args:
            prompt: The prompt to send to the model.
            model_name: The name of the model to use for generation.
            stream: Whether to stream the response.
            think: Whether to enable thinking mode.

        Returns:
            Complete JSON response (if stream=False) or AsyncGenerator of JSON chunks (if stream=True).
            Each response contains 'think', 'content', and 'response' fields.
        """
        ...

    def generate_sync(
        self,
        prompt: str,
        model_name: str,
        think: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Generate text using the model (v1 API) - Synchronous version.

        Args:
            prompt: The prompt to send to the model.
            model_name: The name of the model to use for generation.
            think: Whether to enable thinking mode.

        Returns:
            Complete JSON response. Streaming is not supported in sync version.
            Response contains 'think', 'content', and 'response' fields.
        """
        ...
