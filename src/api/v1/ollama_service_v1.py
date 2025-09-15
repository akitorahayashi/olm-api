import asyncio
import json
import logging
import os
from functools import lru_cache

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
    ):
        """Simple generate response - just prompt in, text out."""
        if stream:
            return StreamingResponse(
                self._stream_generator(prompt, model_name),
                media_type="text/event-stream; charset=utf-8",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        else:
            async with self.semaphore:
                # Simple chat call
                response = await run_in_threadpool(
                    self.client.chat,
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    stream=False,
                )

                # Extract content more flexibly - qwen3:0.6b might return different structure
                content = None
                if isinstance(response, dict):
                    if "message" in response and isinstance(response["message"], dict):
                        content = response["message"].get("content")
                    elif "content" in response:
                        content = response["content"]
                    elif "response" in response:
                        content = response["response"]

                # Fallback: convert entire response to string
                if not content:
                    content = str(response)

                return GenerateResponse(response=content)

    async def _stream_generator(self, prompt: str, model_name: str):
        """Simple streaming - just content chunks."""
        async with self.semaphore:
            response = await run_in_threadpool(
                self.client.chat,
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )

            iterator = await run_in_threadpool(iter, response)
            while True:
                try:
                    chunk = await run_in_threadpool(next, iterator)
                    content = chunk.get("message", {}).get("content")
                    if content:
                        yield f"data: {json.dumps({'response': content})}\n\n"
                except StopIteration:
                    break

    @staticmethod
    @lru_cache
    def get_instance() -> "OllamaServiceV1":
        """Get singleton OllamaServiceV1 instance."""
        settings = get_settings()
        return OllamaServiceV1(settings)
