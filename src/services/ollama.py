import logging

import httpx
import ollama
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from src.config.settings import Settings
from src.schemas.generate import GenerateResponse


async def stream_generator(response_iter):
    """
    Iterate a blocking generator in a threadpool and yield content chunks
    formatted for Server-Sent Events (SSE).
    """
    while True:
        try:
            chunk = await run_in_threadpool(next, response_iter)
        except RuntimeError as e:
            if "StopIteration" in str(e):
                break
            raise
        except StopIteration:
            break

        content = chunk.get("message", {}).get("content")
        if content:
            # Format as SSE: "data: <content>\n\n"
            yield f"data: {content}\n\n"


async def generate_ollama_response(
    prompt: str,
    stream: bool,
    ollama_client: ollama.Client,
    settings: Settings,
):
    """
    Generates a response from the Ollama model, handling both streaming and non-streaming cases.
    """
    try:
        chat_response = await run_in_threadpool(
            ollama_client.chat,
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=stream,
        )

        if stream:
            # Return a streaming response with the correct SSE media type
            return StreamingResponse(
                stream_generator(iter(chat_response)),
                media_type="text/event-stream; charset=utf-8",
            )
        else:
            if "message" in chat_response and "content" in chat_response["message"]:
                response_content = chat_response["message"]["content"]
                return GenerateResponse(response=response_content)
            else:
                raise HTTPException(
                    status_code=500, detail="Invalid response structure from Ollama."
                )

    except (httpx.RequestError, httpx.HTTPStatusError, ollama.RequestError) as e:
        # Catch specific, known exceptions from the client libraries
        error_detail = e.args[0] if e.args else str(e)
        logging.error(f"Ollama API request failed: {error_detail}")
        # Re-raise the original exception so the middleware can capture the full traceback
        raise
    except Exception:
        # Catch any other unexpected errors without leaking details
        logging.exception("Unexpected error in generate_ollama_response")
        raise HTTPException(
            status_code=500, detail="An unexpected internal error occurred."
        )
