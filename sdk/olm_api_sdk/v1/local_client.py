from typing import Any, AsyncGenerator, Dict, Optional, Union

import ollama

from ..utils.thinking_parser import parse_thinking_response


class OlmLocalClientV1:
    """
    A client for interacting with a local `ollama serve` instance using v1 API schema.

    This client converts the project's v1 API schema to direct Ollama calls,
    bypassing the proxy server while maintaining the same interface.
    """

    def __init__(self, host: str = "http://localhost:11434"):
        self.client = ollama.AsyncClient(host=host)

    async def generate(
        self,
        prompt: str,
        model_name: str,
        stream: bool = False,
        think: Optional[bool] = None,
        **options: Any,
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Generate text using local Ollama with v1 schema.

        Args:
            prompt: The prompt to send to the model.
            model_name: The name of the model to use for generation.
            stream: Whether to stream the response.
            think: Whether to enable thinking mode.
            **options: Additional generation parameters to pass to Ollama.

        Returns:
            Complete JSON response (if stream=False) or AsyncGenerator of JSON chunks (if stream=True).
            Each response contains 'think', 'content', and 'response' fields.
        """
        messages = [{"role": "user", "content": prompt}]

        # Add think parameter to options if provided
        if think is not None:
            options["think"] = think

        if stream:
            return self._stream_generate(messages, model_name, **options)
        else:
            return await self._batch_generate(messages, model_name, **options)

    async def _stream_generate(
        self, messages, model_name: str, **options: Any
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate text with streaming from local Ollama, providing structured JSON chunks."""
        stream = await self.client.chat(
            model=model_name, messages=messages, stream=True, options=options
        )
        accumulated_content = ""

        async for chunk in stream:
            if content := chunk["message"]["content"]:
                accumulated_content += content

                # Parse current accumulated content
                parsed = parse_thinking_response(accumulated_content)

                # Send unified response matching API server format
                response_data = {
                    "think": parsed["thinking"],
                    "content": parsed["content"],
                    "full_response": accumulated_content,
                }
                yield response_data

    async def _batch_generate(
        self, messages, model_name: str, **options: Any
    ) -> Dict[str, Any]:
        """Generate complete text response from local Ollama with structured JSON format."""
        response = await self.client.chat(
            model=model_name, messages=messages, stream=False, options=options
        )
        raw_content = response["message"]["content"]

        # Parse thinking vs content using same logic as API server
        parsed = parse_thinking_response(raw_content)

        return {
            "think": parsed["thinking"],
            "content": parsed["content"],
            "full_response": raw_content,
        }
