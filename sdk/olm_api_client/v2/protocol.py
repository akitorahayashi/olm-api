from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Optional,
    Protocol,
    Union,
    runtime_checkable,
)


@runtime_checkable
class OlmClientV2Protocol(Protocol):
    """
    Protocol for Olm API v2 clients.

    Provides OpenAI-compatible chat completion functionality with advanced features
    including conversation history, tool calling, and fine-grained generation control.
    """

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        model_name: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """
        Generate chat completion using the v2 API with OpenAI-compatible format.

        Args:
            messages: List of message dictionaries with role and content.
            model_name: The name of the model to use for generation.
            tools: Optional list of tool definitions for function calling.
            stream: Whether to stream the response.
            **kwargs: Additional generation parameters (temperature, top_p, etc.).

        Returns:
            Complete response dict (if stream=False) or AsyncGenerator (if stream=True).
        """
        ...
