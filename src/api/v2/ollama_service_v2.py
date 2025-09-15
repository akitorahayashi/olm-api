import asyncio
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
from src.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class OllamaServiceV2:
    """
    OllamaService specifically designed for v2 API endpoints.

    Provides OpenAI-compatible chat completion functionality with proper
    support for tool calling, thought/answer distinction, and structured streaming.
    """

    def __init__(self, settings: Settings):
        host = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
        self.client = ollama.Client(host=host)
        if settings.CONCURRENT_REQUEST_LIMIT < 1:
            raise ValueError("CONCURRENT_REQUEST_LIMIT must be at least 1")
        self.semaphore = asyncio.BoundedSemaphore(settings.CONCURRENT_REQUEST_LIMIT)

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **options,
    ) -> Union[Dict[str, Any], StreamingResponse]:
        """
        Chat completion method for v2 API.
        Provides OpenAI-compatible responses with proper tool calling support.
        """
        if stream:
            return StreamingResponse(
                self._chat_completion_stream_generator(
                    messages, model, tools, **options
                ),
                media_type="text/event-stream; charset=utf-8",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        else:
            async with self.semaphore:
                try:
                    # Build parameters for ollama.chat call
                    chat_params = {
                        "model": model,
                        "messages": messages,
                        "stream": False,
                    }

                    # Add tools if provided
                    if tools:
                        chat_params["tools"] = tools

                    # Add additional options
                    if options:
                        chat_params["options"] = options

                    chat_response = await run_in_threadpool(
                        self.client.chat, **chat_params
                    )

                    # Transform to OpenAI-compatible format
                    return self._transform_ollama_response_to_openai(
                        chat_response, model
                    )

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
                    "messages": messages,
                    "stream": True,
                }

                # Add tools if provided
                if tools:
                    chat_params["tools"] = tools

                # Add additional options
                if options:
                    chat_params["options"] = options

                chat_response = await run_in_threadpool(self.client.chat, **chat_params)
                iterator = await run_in_threadpool(iter, chat_response)

                created_time = int(time.time())
                created_id = f"chatcmpl-{created_time}"

                while True:
                    try:
                        chunk = await run_in_threadpool(next, iterator)
                        # Transform chunk to OpenAI-compatible streaming format
                        stream_chunk = self._transform_ollama_chunk_to_openai(
                            chunk, model, created_id, created_time
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

    def _transform_ollama_response_to_openai(
        self, ollama_response: Dict[str, Any], model: str
    ) -> Dict[str, Any]:
        """Transform Ollama response to OpenAI-compatible format."""
        message = ollama_response.get("message", {})

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
                        "content": message.get("content"),
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

    def _transform_ollama_chunk_to_openai(
        self,
        ollama_chunk: Dict[str, Any],
        model: str,
        created_id: str,
        created_time: int,
    ) -> Dict[str, Any]:
        """
        Transform Ollama streaming chunk to OpenAI-compatible format.

        Properly handles tool_calls to enable thought/answer distinction:
        - When tool_calls are present: thought mode (save_thought function)
        - When content is present: answer mode (direct response)
        """
        message = ollama_chunk.get("message", {})

        # Build delta object with all possible fields
        delta = {}

        # Add role if present
        if message.get("role"):
            delta["role"] = message.get("role")

        # Add content if present - this indicates "answer" mode
        if message.get("content"):
            delta["content"] = message.get("content")

        # Add tool_calls if present - this indicates "thought" mode
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
