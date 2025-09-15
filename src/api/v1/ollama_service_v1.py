import asyncio
import json
import logging
import os
from functools import lru_cache
from typing import Optional

from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

import ollama
from src.api.v1.schemas import GenerateResponse
from src.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class OllamaServiceV1:
    """Simple Ollama service for v1 API - direct prompt to response."""

    def __init__(self, settings: Settings):
        host = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
        self.client = ollama.Client(host=host)
        if settings.CONCURRENT_REQUEST_LIMIT < 1:
            raise ValueError("CONCURRENT_REQUEST_LIMIT must be at least 1")
        self.semaphore = asyncio.BoundedSemaphore(settings.CONCURRENT_REQUEST_LIMIT)

    async def generate_response(
        self,
        prompt: str,
        model_name: str,
        stream: bool = False,
        think: Optional[bool] = None,
    ):
        """Simple generate response - just prompt in, text out."""
        if stream:
            return StreamingResponse(
                self._stream_generator(prompt, model_name, think),
                media_type="text/event-stream; charset=utf-8",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        else:
            async with self.semaphore:
                # Simple chat call
                chat_params = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                }
                if think is not None:
                    chat_params["think"] = think

                response = await run_in_threadpool(self.client.chat, **chat_params)

                # Extract content properly from ollama response
                if hasattr(response, "message") and hasattr(
                    response.message, "content"
                ):
                    raw_content = response.message.content or ""
                else:
                    raw_content = ""

                # Parse thinking vs content
                from src.utils.thinking_parser import parse_thinking_response

                parsed = parse_thinking_response(raw_content)

                return GenerateResponse(
                    think=parsed["thinking"],
                    content=parsed["content"],
                    response=raw_content,
                )

    async def _stream_generator(
        self, prompt: str, model_name: str, think: Optional[bool] = None
    ):
        """Simple streaming - just content chunks."""
        async with self.semaphore:
            chat_params = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
            }
            if think is not None:
                chat_params["think"] = think

            response = await run_in_threadpool(self.client.chat, **chat_params)

            iterator = await run_in_threadpool(iter, response)
            accumulated_content = ""

            while True:
                try:
                    chunk = await run_in_threadpool(next, iterator)
                    chunk_content = self._extract_content_from_chunk(chunk)
                    if chunk_content:
                        accumulated_content += chunk_content

                        # Parse current accumulated content
                        from src.utils.thinking_parser import parse_thinking_response

                        parsed = parse_thinking_response(accumulated_content)

                        # Send unified response
                        response_data = {
                            "think": parsed["thinking"],
                            "content": parsed["content"],
                            "response": accumulated_content,
                        }
                        yield f"data: {json.dumps(response_data)}\n\n"
                except StopIteration:
                    break

    def _extract_content_from_response(self, response) -> str:
        """
        Extract content from ollama response object.
        """
        try:
            # Force return string representation for debugging
            return str(response)

        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            return ""

    def _extract_content_from_chunk(self, chunk) -> str:
        """
        Extract content from ollama streaming chunk.

        Handles both dict format and ollama chunk objects.
        """
        try:
            # Try to access as ollama chunk object first
            if hasattr(chunk, "message") and hasattr(chunk.message, "content"):
                return chunk.message.content or ""

            # Fallback to dict format
            if isinstance(chunk, dict):
                return chunk.get("message", {}).get("content", "")

            return ""

        except Exception as e:
            logger.error(f"Error extracting content from ollama chunk: {e}")
            return ""

    @staticmethod
    @lru_cache
    def get_instance() -> "OllamaServiceV1":
        """Get singleton OllamaServiceV1 instance."""
        settings = get_settings()
        return OllamaServiceV1(settings)
