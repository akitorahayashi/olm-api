import logging

import httpx
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

import ollama
from src.schemas.generate import GenerateResponse


async def stream_generator(response_iter):
    """
    Iterate a blocking generator in a threadpool and yield content chunks
    formatted for Server-Sent Events (SSE).
    """
    # This function is designed to run in a threadpool, so it's safe to use
    # a standard try/except block for the generator.
    try:
        for chunk in response_iter:
            content = chunk.get("message", {}).get("content")
            if content:
                # Format as SSE: "data: <content>\n\n"
                yield f"data: {content}\n\n"
    except (httpx.RequestError, ollama.ResponseError):
        # If an error occurs during streaming, log it and re-raise.
        # The global exception handler will not catch exceptions from streaming responses,
        # but re-raising ensures the connection is terminated correctly.
        logging.exception("Error during Ollama response streaming.")
        raise


async def generate_ollama_response(
    prompt: str,
    model_name: str,
    stream: bool,
    ollama_client: ollama.Client,
):
    """
    Generates a response from the Ollama model.
    Exceptions are caught by the global exception handler in main.py.
    """
    chat_response = await run_in_threadpool(
        ollama_client.chat,
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        stream=stream,
    )

    if stream:
        # For streaming responses, we return a generator function that will be
        # executed by the StreamingResponse.
        return StreamingResponse(
            stream_generator(iter(chat_response)),
            media_type="text/event-stream; charset=utf-8",
        )
    else:
        # For non-streaming, we process the response directly.
        if "message" in chat_response and "content" in chat_response["message"]:
            response_content = chat_response["message"]["content"]
            return GenerateResponse(response=response_content)
        else:
            # If the response structure is invalid, log it and let the unhandled
            # exception be caught by a generic 500 handler if necessary.
            # However, this case should ideally not happen with a healthy Ollama service.
            logging.error(f"Invalid response structure from Ollama: {chat_response}")
            # This will result in a generic 500 error, which is appropriate.
            raise ValueError("Invalid response structure from Ollama.")


async def pull_model(model_name: str, ollama_client: ollama.Client):
    """
    Pulls a model from the Ollama registry.
    Exceptions are caught by the global exception handler in main.py.
    """
    # This is a blocking call, so run it in a threadpool
    return await run_in_threadpool(ollama_client.pull, model=model_name)


async def list_models(ollama_client: ollama.Client):
    """
    Lists all models available locally in Ollama.
    Exceptions are caught by the global exception handler in main.py.
    """
    return await run_in_threadpool(ollama_client.list)


async def delete_model(model_name: str, ollama_client: ollama.Client):
    """
    Deletes a model from Ollama.
    Exceptions are caught by the global exception handler in main.py.
    """
    await run_in_threadpool(ollama_client.delete, model=model_name)
