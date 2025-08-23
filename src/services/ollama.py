import ollama
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from src.config.settings import Settings
from src.schemas.generate import GenerateResponse


async def stream_generator(response_iter):
    """
    Iterate a blocking generator in a threadpool and yield content chunks.
    """
    while True:
        try:
            # Run the blocking `next()` call in a thread pool
            chunk = await run_in_threadpool(next, response_iter)
        except RuntimeError as e:
            # run_in_threadpool can wrap StopIteration in a RuntimeError
            if "StopIteration" in str(e):
                break
            raise  # Re-raise other runtime errors
        except StopIteration:
            # Catch StopIteration as a fallback
            break
        content = chunk.get("message", {}).get("content")
        if content:
            yield content


async def generate_ollama_response(
    prompt: str,
    stream: bool,
    ollama_client: ollama.Client,
    settings: Settings,
):
    """
    Generates a response from the Ollama model, handling both streaming and non-streaming cases.
    It runs the blocking I/O calls in a threadpool to avoid blocking the event loop.
    """
    try:
        # Run the blocking `ollama_client.chat` call in a thread pool
        chat_response = await run_in_threadpool(
            ollama_client.chat,
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=stream,
        )

        if stream:
            return StreamingResponse(
                stream_generator(iter(chat_response)),
                media_type="text/event-stream",
            )
        else:
            if "message" in chat_response and "content" in chat_response["message"]:
                response_content = chat_response["message"]["content"]
                return GenerateResponse(response=response_content)
            else:
                raise HTTPException(
                    status_code=500, detail="Invalid response structure from Ollama."
                )

    except ollama.ResponseError as e:
        error_detail = e.args[0] if e.args else str(e)
        raise HTTPException(
            status_code=500,
            detail=f"Ollama API error: {error_detail}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )
