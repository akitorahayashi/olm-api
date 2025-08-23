import ollama
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from src.config.settings import Settings
from src.schemas.generate import GenerateResponse


async def stream_generator(response_stream):
    """
    Asynchronous generator to process and send streaming responses from Ollama.
    """
    for chunk in response_stream:
        # Check if the content key exists and is not empty
        if chunk.get("message", {}).get("content"):
            yield chunk["message"]["content"]


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
        chat_response = ollama_client.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=stream,
        )

        if stream:
            return StreamingResponse(
                stream_generator(chat_response),
                media_type="text/event-stream",
            )
        else:
            # Ensure the response structure is as expected before accessing content
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
        # Catching any other unexpected errors
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )
