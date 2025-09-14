import asyncio
import json
import logging
import os
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

import ollama
from src.config.settings import Settings, get_settings


class GenerateResponse(BaseModel):
    response: str


class OllamaService:
    def __init__(self, settings: Settings):
        host = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
        self.client = ollama.Client(host=host)
        if settings.CONCURRENT_REQUEST_LIMIT < 1:
            raise ValueError("CONCURRENT_REQUEST_LIMIT must be at least 1")
        self.semaphore = asyncio.BoundedSemaphore(settings.CONCURRENT_REQUEST_LIMIT)

    async def _chat_stream_generator(self, prompt: str, model_name: str):
        """
        Processes a streaming response from `ollama.chat` and yields SSE events.
        Handles client disconnects silently.
        Manages semaphore for the entire streaming duration.
        """
        async with self.semaphore:
            try:
                chat_response = await run_in_threadpool(
                    self.client.chat,
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                )
                iterator = await run_in_threadpool(iter, chat_response)
                while True:
                    try:
                        chunk = await run_in_threadpool(next, iterator)
                        content = chunk.get("message", {}).get("content")
                        if content:
                            sse_data = {"response": content}
                            yield f"data: {json.dumps(sse_data)}\n\n"
                    except StopIteration:
                        break
            except asyncio.CancelledError:
                return
            except ollama.ResponseError as e:
                error_message = e.args[0] if e.args else "Unknown error"
                status_code = e.args[1] if len(e.args) > 1 else "N/A"
                logging.error(
                    f"Ollama API request failed during streaming. Status: {status_code}, "
                    f"Response: {error_message}"
                )
                raise
            except httpx.RequestError as e:
                logging.error(f"Unable to connect to Ollama API during streaming: {e}")
                raise
            except Exception:
                logging.exception(
                    "An unexpected error occurred during Ollama streaming."
                )
                raise

    async def generate_response(
        self,
        prompt: str,
        model_name: str,
        stream: bool,
    ):
        """
        Generates a response from the Ollama model, with concurrency limiting.
        """
        if stream:
            return StreamingResponse(
                self._chat_stream_generator(prompt, model_name),
                media_type="text/event-stream; charset=utf-8",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        else:
            async with self.semaphore:
                try:
                    chat_response = await run_in_threadpool(
                        self.client.chat,
                        model=model_name,
                        messages=[{"role": "user", "content": prompt}],
                        stream=False,
                    )
                except ollama.ResponseError as e:
                    error_message = e.args[0] if e.args else "Unknown error"
                    status_code = e.args[1] if len(e.args) > 1 else "N/A"
                    logging.error(
                        f"Ollama API request failed. Status: {status_code}, "
                        f"Response: {error_message}"
                    )
                    raise
                except httpx.RequestError as e:
                    logging.error(f"Unable to connect to Ollama API: {e}")
                    raise
                except Exception:
                    logging.exception("An unexpected error occurred in OllamaService")
                    raise

                if "message" in chat_response and "content" in chat_response["message"]:
                    response_content = chat_response["message"]["content"]
                    return GenerateResponse(response=response_content)
                else:
                    logging.error(
                        f"Invalid response structure from Ollama: {chat_response}"
                    )
                    raise ValueError("Invalid response structure from Ollama.")

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
        Provides safe passthrough to ollama.chat with v2 contract.
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
                    logging.error(
                        f"Ollama API request failed in chat_completion. Status: {status_code}, "
                        f"Response: {error_message}"
                    )
                    raise
                except httpx.RequestError as e:
                    logging.error(
                        f"Unable to connect to Ollama API in chat_completion: {e}"
                    )
                    raise
                except Exception:
                    logging.exception("An unexpected error occurred in chat_completion")
                    raise

    async def _chat_completion_stream_generator(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        **options,
    ):
        """
        Streaming generator for v2 chat completion API.
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

                while True:
                    try:
                        chunk = await run_in_threadpool(next, iterator)
                        # Transform chunk to OpenAI-compatible streaming format
                        stream_chunk = self._transform_ollama_chunk_to_openai(
                            chunk, model
                        )
                        yield f"data: {json.dumps(stream_chunk)}\n\n"
                    except StopIteration:
                        # Send final chunk
                        final_chunk = {
                            "id": f"chatcmpl-{int(time.time())}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
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
                logging.error(
                    f"Ollama API request failed during chat completion streaming. Status: {status_code}, "
                    f"Response: {error_message}"
                )
                raise
            except httpx.RequestError as e:
                logging.error(
                    f"Unable to connect to Ollama API during chat completion streaming: {e}"
                )
                raise
            except Exception:
                logging.exception(
                    "An unexpected error occurred during Ollama chat completion streaming."
                )
                raise

    def _transform_ollama_response_to_openai(
        self, ollama_response: Dict[str, Any], model: str
    ) -> Dict[str, Any]:
        """Transform Ollama response to OpenAI-compatible format."""
        message = ollama_response.get("message", {})

        # Handle tool calls if present
        tool_calls = None
        if "tool_calls" in message and message["tool_calls"]:
            tool_calls = message["tool_calls"]

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
                        "tool_calls": tool_calls,
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
        self, ollama_chunk: Dict[str, Any], model: str
    ) -> Dict[str, Any]:
        """Transform Ollama streaming chunk to OpenAI-compatible format."""
        message = ollama_chunk.get("message", {})

        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": message.get("role") if message.get("role") else None,
                        "content": message.get("content"),
                    },
                    "finish_reason": None,
                }
            ],
        }

    async def list_models(self):
        """
        Lists all models available locally in Ollama.
        """
        return await run_in_threadpool(self.client.list)


@lru_cache
def get_ollama_service() -> OllamaService:
    """
    Dependency provider for the OllamaService.

    This function returns a singleton instance of the OllamaService.
    Using @lru_cache without arguments ensures that the same instance is returned
    for every call, making it a singleton across the application's lifecycle.

    It directly calls get_settings() to obtain the application settings.
    This is a clean and testable way to inject dependencies into a singleton,
    as the get_settings dependency can be mocked during tests.
    """
    settings = get_settings()
    return OllamaService(settings)
