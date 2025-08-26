import asyncio
import json
import logging
import os
from functools import lru_cache

import httpx
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

import ollama
from src.api.v1.schemas import GenerateResponse


class OllamaService:
    def __init__(self):
        host = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
        self.client = ollama.Client(host=host)

    async def _chat_stream_generator(self, response_iter):
        """
        Processes a streaming response from `ollama.chat` and yields SSE events.
        Handles client disconnects silently.
        """
        try:
            iterator = await run_in_threadpool(iter, response_iter)
            while True:
                try:
                    chunk = await run_in_threadpool(next, iterator)
                    content = chunk.get("message", {}).get("content")
                    if content:
                        # SSE spec requires multi-line data to be sent as separate
                        # 'data:' fields, terminated by a double newline.
                        lines = content.split("\n")
                        for line in lines:
                            yield f"data: {line}\n"
                        yield "\n"
                except StopIteration:
                    break
        except asyncio.CancelledError:
            # This block is entered when the client disconnects.
            # No logging is needed, as this is an expected scenario.
            return
        except (httpx.RequestError, ollama.ResponseError):
            logging.exception("Error during Ollama chat response streaming.")
            raise

    async def _non_chat_stream_generator(self, response_iter):
        """
        Processes a generic streaming response (e.g., for pull) and yields
        each JSON chunk as an SSE event. Handles client disconnects silently.
        """
        try:
            iterator = await run_in_threadpool(iter, response_iter)
            while True:
                try:
                    chunk = await run_in_threadpool(next, iterator)
                    yield f"data: {json.dumps(chunk)}\n\n"
                except StopIteration:
                    break
        except asyncio.CancelledError:
            # Client disconnected, which is expected. No error logging needed.
            return
        except (httpx.RequestError, ollama.ResponseError):
            logging.exception("Error during Ollama non-chat response streaming.")
            raise

    async def generate_response(
        self,
        prompt: str,
        model_name: str,
        stream: bool,
    ):
        """
        Generates a response from the Ollama model.
        """
        chat_response = await run_in_threadpool(
            self.client.chat,
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            stream=stream,
        )

        if stream:
            return StreamingResponse(
                self._chat_stream_generator(chat_response),
                media_type="text/event-stream; charset=utf-8",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        else:
            if "message" in chat_response and "content" in chat_response["message"]:
                response_content = chat_response["message"]["content"]
                return GenerateResponse(response=response_content)
            else:
                logging.error(
                    f"Invalid response structure from Ollama: {chat_response}"
                )
                raise ValueError("Invalid response structure from Ollama.")

    async def pull_model(self, model_name: str, stream: bool):
        """
        Pulls a model from the Ollama registry. Can be streaming or blocking.
        """
        pull_response = await run_in_threadpool(
            self.client.pull, model=model_name, stream=stream
        )

        if stream:
            return StreamingResponse(
                self._non_chat_stream_generator(pull_response),
                media_type="text/event-stream; charset=utf-8",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        else:
            # If not streaming, the response is the final status dictionary.
            return pull_response

    async def list_models(self):
        """
        Lists all models available locally in Ollama.
        """
        return await run_in_threadpool(self.client.list)

    async def delete_model(self, model_name: str):
        """
        Deletes a model from Ollama.
        """
        await run_in_threadpool(self.client.delete, model=model_name)


@lru_cache(maxsize=1)
def get_ollama_service() -> OllamaService:
    """
    Dependency provider for the OllamaService.
    Using lru_cache(maxsize=1) makes the singleton intent explicit.
    """
    return OllamaService()
