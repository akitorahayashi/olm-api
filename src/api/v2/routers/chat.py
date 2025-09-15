from typing import Union

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from src.api.v2.ollama_service_v2 import OllamaServiceV2
from src.api.v2.schemas.request import ChatRequest
from src.api.v2.schemas.response import ChatResponse

router = APIRouter(
    prefix="/api/v2",
    tags=["chat"],
)


@router.post("/chat", response_model=ChatResponse)
async def chat_completions(
    request: ChatRequest,
    ollama_service: OllamaServiceV2 = Depends(OllamaServiceV2.get_instance),
) -> Union[ChatResponse, StreamingResponse]:
    """
    Chat completions endpoint compatible with OpenAI API.

    Supports:
    - Messages array (system, user, assistant, tool roles)
    - Tool calling with function definitions
    - Streaming responses
    - Temperature, top_p, max_tokens, and other generation parameters
    """
    try:
        # Convert Pydantic models to dict for service layer
        messages = [message.model_dump() for message in request.messages]
        tools = [tool.model_dump() for tool in request.tools] if request.tools else None

        # Build options dict from request parameters
        options = request.options or {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.top_p is not None:
            options["top_p"] = request.top_p
        if request.top_k is not None:
            options["top_k"] = request.top_k
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens
        if request.stop is not None:
            options["stop"] = request.stop

        return await ollama_service.chat_completion(
            messages=messages,
            model=request.model,
            tools=tools,
            stream=request.stream,
            **options,
        )

    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
