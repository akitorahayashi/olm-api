import logging

import httpx
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

import ollama
from src.schemas.generate import GenerateResponse


class OllamaService:
    def __init__(self, host: str = "http://ollama:11434"):
        self.client = ollama.Client(host=host)

    async def _stream_generator(self, response_iter):
        """
        Iterate a blocking generator in a threadpool and yield content chunks
        formatted for Server-Sent Events (SSE).
        """
        try:
            for chunk in response_iter:
                content = chunk.get("message", {}).get("content")
                if content:
                    yield f"data: {content}\n\n"
        except (httpx.RequestError, ollama.ResponseError):
            logging.exception("Error during Ollama response streaming.")
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
                self._stream_generator(iter(chat_response)),
                media_type="text/event-stream; charset=utf-8",
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

    async def pull_model(self, model_name: str):
        """
        Pulls a model from the Ollama registry.
        """
        return await run_in_threadpool(self.client.pull, model=model_name)

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
