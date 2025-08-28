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
from src.config.settings import Settings, get_settings


class OllamaService:
    def __init__(self, settings: Settings):
        host = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
        self.client = ollama.Client(host=host)
        self.semaphore = asyncio.Semaphore(settings.OLLAMA_CONCURRENT_REQUEST_LIMIT)

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
            logging.exception("An unexpected error occurred during Ollama streaming.")
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
        async with self.semaphore:
            try:
                chat_response = await run_in_threadpool(
                    self.client.chat,
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    stream=stream,
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
