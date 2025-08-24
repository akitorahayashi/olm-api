import logging

import httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

import ollama
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
    model_name: str,
    stream: bool,
    ollama_client: ollama.Client,
):
    """
    Generates a response from the Ollama model, handling both streaming and non-streaming cases.
    """
    try:
        chat_response = await run_in_threadpool(
            ollama_client.chat,
            model=model_name,
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


async def pull_model(model_name: str, ollama_client: ollama.Client):
    """Pulls a model from the Ollama registry."""
    try:
        # This is a blocking call, so run it in a threadpool
        return await run_in_threadpool(ollama_client.pull, model=model_name)
    except ollama.RequestError as e:
        raise HTTPException(
            status_code=404, detail=f"Model '{model_name}' not found in registry."
        ) from e
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        error_detail = e.args[0] if e.args else str(e)
        logging.error(f"Ollama API request failed during pull: {error_detail}")
        raise HTTPException(
            status_code=500, detail="Failed to communicate with Ollama."
        ) from e


async def list_models(ollama_client: ollama.Client):
    """Lists all models available locally in Ollama."""
    try:
        return await run_in_threadpool(ollama_client.list)
    except (httpx.RequestError, httpx.HTTPStatusError, ollama.RequestError) as e:
        error_detail = e.args[0] if e.args else str(e)
        logging.error(f"Ollama API request failed during list: {error_detail}")
        raise HTTPException(
            status_code=500, detail="Failed to communicate with Ollama."
        ) from e


async def delete_model(model_name: str, ollama_client: ollama.Client):
    """Deletes a model from Ollama."""
    try:
        await run_in_threadpool(ollama_client.delete, model=model_name)
    except ollama.RequestError as e:
        # Ollama's client raises a RequestError for 404 Not Found
        raise HTTPException(
            status_code=404, detail=f"Model '{model_name}' not found."
        ) from e
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        error_detail = e.args[0] if e.args else str(e)
        logging.error(f"Ollama API request failed during delete: {error_detail}")
        raise HTTPException(
            status_code=500, detail="Failed to communicate with Ollama."
        ) from e
