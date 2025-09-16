import asyncio
import base64
import json
import logging
import os
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

import ollama

from ...config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class OllamaServiceV2:
    """
    OllamaService specifically designed for v2 API endpoints.

    Provides chat completion functionality with proper
    support for tool calling, thought/answer distinction, and structured streaming.
    """

    def __init__(self, settings: Settings):
        host = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
        # Initialize ollama client with extended timeout for vision models
        self.client = ollama.Client(
            host=host, timeout=300.0  # 5 minutes timeout for heavy vision models
        )
        if settings.CONCURRENT_REQUEST_LIMIT < 1:
            raise ValueError("CONCURRENT_REQUEST_LIMIT must be at least 1")
        self.semaphore = asyncio.BoundedSemaphore(settings.CONCURRENT_REQUEST_LIMIT)

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        think: Optional[bool] = None,
        **options,
    ) -> Union[Dict[str, Any], StreamingResponse]:
        """
        Chat completion method for v2 API.
        Provides responses with proper tool calling support.
        """
        if stream:
            return StreamingResponse(
                self._chat_completion_stream_generator(
                    messages, model, tools, think, **options
                ),
                media_type="text/event-stream; charset=utf-8",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        else:
            async with self.semaphore:
                try:
                    # Prepare messages and validate images first
                    prepared_messages = self._prepare_messages_for_ollama(messages)

                    # Check if any message contains images
                    has_images = any(msg.get("images") for msg in prepared_messages)

                    # Build parameters for ollama.chat call
                    chat_params = {
                        "model": model,
                        "messages": prepared_messages,
                        "stream": False,
                    }

                    # Add tools if provided
                    if tools:
                        chat_params["tools"] = tools

                    # Add think parameter if provided
                    if think is not None:
                        chat_params["think"] = think

                    # Add additional options with vision-specific adjustments
                    if options:
                        chat_params["options"] = options

                    # For vision models with images, adjust options for better handling
                    if has_images:
                        if "options" not in chat_params:
                            chat_params["options"] = {}
                        # Add vision-specific options
                        chat_params["options"].setdefault(
                            "num_predict", 512
                        )  # Limit tokens for vision
                        chat_params["options"].setdefault(
                            "temperature", 0.7
                        )  # Moderate creativity
                        chat_params["options"] = options

                    chat_response = await run_in_threadpool(
                        self.client.chat, **chat_params
                    )

                    # Transform response format
                    return self._transform_ollama_response(chat_response, model)

                except ollama.ResponseError as e:
                    error_message = e.args[0] if e.args else "Unknown error"
                    status_code = e.args[1] if len(e.args) > 1 else "N/A"
                    logger.error(
                        f"Ollama API request failed in chat_completion. Status: {status_code}, "
                        f"Response: {error_message}"
                    )
                    raise HTTPException(status_code=502, detail=error_message)
                except httpx.RequestError as e:
                    logger.error(
                        f"Unable to connect to Ollama API in chat_completion: {e}"
                    )
                    raise HTTPException(
                        status_code=503, detail="Unable to connect to Ollama API"
                    )
                except Exception:
                    logger.exception("An unexpected error occurred in chat_completion")
                    raise HTTPException(status_code=500, detail="Internal server error")

    async def _chat_completion_stream_generator(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        think: Optional[bool] = None,
        **options,
    ):
        """
        Streaming generator for v2 chat completion API.
        Properly handles tool_calls and content distinction for thought/answer separation.
        """
        async with self.semaphore:
            try:
                # Build parameters for ollama.chat call
                chat_params = {
                    "model": model,
                    "messages": self._prepare_messages_for_ollama(messages),
                    "stream": True,
                }

                # Add tools if provided
                if tools:
                    chat_params["tools"] = tools

                # Add think parameter if provided
                if think is not None:
                    chat_params["think"] = think

                # Add additional options
                if options:
                    chat_params["options"] = options

                chat_response = await run_in_threadpool(self.client.chat, **chat_params)
                iterator = await run_in_threadpool(iter, chat_response)

                created_time = int(time.time())
                created_id = f"chatcmpl-{created_time}"
                accumulated_content = ""

                while True:
                    try:
                        chunk = await run_in_threadpool(next, iterator)

                        # Update accumulated content
                        chunk_content = chunk.get("message", {}).get("content", "")
                        if chunk_content:
                            accumulated_content += chunk_content

                        # Transform chunk to streaming format
                        stream_chunk = self._transform_ollama_chunk(
                            chunk, model, created_id, created_time, accumulated_content
                        )
                        yield f"data: {json.dumps(stream_chunk)}\n\n"
                    except StopIteration:
                        # Send final chunk
                        final_chunk = {
                            "id": created_id,
                            "object": "chat.completion.chunk",
                            "created": created_time,
                            "model": model,
                            "choices": [
                                {"index": 0, "delta": {}, "finish_reason": "stop"}
                            ],
                        }
                        yield f"data: {json.dumps(final_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                        break

            except asyncio.CancelledError:
                return
            except ollama.ResponseError as e:
                error_message = e.args[0] if e.args else "Unknown error"
                status_code = e.args[1] if len(e.args) > 1 else "N/A"
                logger.error(
                    f"Ollama API request failed during chat completion streaming. Status: {status_code}, "
                    f"Response: {error_message}"
                )
                raise HTTPException(status_code=502, detail=error_message)
            except httpx.RequestError as e:
                logger.error(
                    f"Unable to connect to Ollama API during chat completion streaming: {e}"
                )
                raise HTTPException(
                    status_code=503, detail="Unable to connect to Ollama API"
                )
            except Exception:
                logger.exception(
                    "An unexpected error occurred during Ollama chat completion streaming."
                )
                raise HTTPException(status_code=500, detail="Internal server error")

    def _prepare_messages_for_ollama(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Prepare messages for ollama client by handling images field.

        Converts message format from API schema to ollama-compatible format.
        Validates base64 image data and limits number of images.
        """
        prepared_messages = []

        for message in messages:
            # Create a copy of the message
            prepared_message = message.copy()

            # If message has images, validate and add them to the ollama format
            images = message.get("images")
            if images:
                try:
                    validated_images = self._validate_images(images)
                    prepared_message["images"] = validated_images
                except ValueError as e:
                    logger.warning(f"Invalid image data: {e}")
                    raise HTTPException(status_code=400, detail=str(e))

                # Clean up - remove None images field if it exists
                if "images" in prepared_message and prepared_message["images"] is None:
                    del prepared_message["images"]

            prepared_messages.append(prepared_message)

        return prepared_messages

    def _validate_images(self, images: List[str]) -> List[str]:
        """
        Validate base64 image data and limit number of images.

        Args:
            images: List of base64 encoded image strings

        Returns:
            List of validated base64 image strings

        Raises:
            ValueError: If image data is invalid or too many images
        """
        if not images:
            return []

        # Limit number of images to prevent resource exhaustion
        max_images = 5
        if len(images) > max_images:
            raise ValueError(f"Too many images. Maximum {max_images} images allowed.")

        validated_images = []
        for i, image_data in enumerate(images):
            if not isinstance(image_data, str):
                raise ValueError(f"Image {i + 1}: Image data must be a string")

            if not image_data.strip():
                raise ValueError(f"Image {i + 1}: Image data cannot be empty")

            # Validate base64 format
            try:
                # Try to decode the base64 data
                decoded_data = base64.b64decode(image_data, validate=True)

                # Check if it's a reasonable size (not too small, not too large)
                if len(decoded_data) < 100:  # Too small to be a valid image
                    raise ValueError(
                        f"Image {i + 1}: Image data appears to be too small"
                    )

                if len(decoded_data) > 10 * 1024 * 1024:  # 10MB limit
                    raise ValueError(f"Image {i + 1}: Image data too large (max 10MB)")

                validated_images.append(image_data)

            except Exception as e:
                raise ValueError(f"Image {i + 1}: Invalid base64 image data - {str(e)}")

        return validated_images

    def _transform_ollama_response(
        self, ollama_response: Dict[str, Any], model: str
    ) -> Dict[str, Any]:
        """Transform Ollama response to chat completion format."""
        message = ollama_response.get("message", {})
        raw_content = message.get("content", "")

        # Parse thinking vs content
        from ...utils.thinking_parser import parse_thinking_response

        parsed = parse_thinking_response(raw_content)

        # Handle tool calls if present
        tool_calls = message.get("tool_calls")

        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": message.get("role", "assistant"),
                        "content": parsed["content"],
                        "think": parsed["thinking"],
                        "response": raw_content,
                        **({"tool_calls": tool_calls} if tool_calls else {}),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": ollama_response.get("prompt_eval_count", 0),
                "completion_tokens": ollama_response.get("eval_count", 0),
                "total_tokens": ollama_response.get("prompt_eval_count", 0)
                + ollama_response.get("eval_count", 0),
            },
        }

    def _transform_ollama_chunk(
        self,
        ollama_chunk: Dict[str, Any],
        model: str,
        created_id: str,
        created_time: int,
        accumulated_content: str = "",
    ) -> Dict[str, Any]:
        """
        Transform Ollama streaming chunk to streaming format with thinking separation.
        """
        message = ollama_chunk.get("message", {})
        chunk_content = message.get("content", "")

        # Update accumulated content
        if chunk_content:
            accumulated_content += chunk_content

        # Parse current accumulated content for thinking
        from ...utils.thinking_parser import parse_thinking_response

        parsed = parse_thinking_response(accumulated_content)

        # Build delta object with thinking separation
        delta = {}

        # Add role if present
        if message.get("role"):
            delta["role"] = message.get("role")

        # Add separated content
        if chunk_content:
            delta["content"] = parsed["content"]
            delta["think"] = parsed["thinking"]
            delta["response"] = accumulated_content

        # Add tool_calls if present
        if message.get("tool_calls"):
            delta["tool_calls"] = message.get("tool_calls")

        return {
            "id": created_id,
            "object": "chat.completion.chunk",
            "created": created_time,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": delta,
                    "finish_reason": None,
                }
            ],
        }

    async def list_models(self):
        """
        Lists all models available locally in Ollama.
        """
        return await run_in_threadpool(self.client.list)

    @staticmethod
    @lru_cache
    def get_instance() -> "OllamaServiceV2":
        """
        Get singleton OllamaServiceV2 instance.

        This method returns a singleton instance of the OllamaServiceV2.
        Using @lru_cache without arguments ensures that the same instance is returned
        for every call, making it a singleton across the application's lifecycle.
        """
        settings = get_settings()
        return OllamaServiceV2(settings)
