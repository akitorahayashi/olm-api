from typing import Union

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.api.v1.services.ollama_service import (
    GenerateResponse,
    OllamaService,
    get_ollama_service,
)


class GenerateRequest(BaseModel):
    prompt: str
    model_name: str
    stream: bool = False


router = APIRouter(
    prefix="/api/v1",
    tags=["generate"],
)


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    ollama_service: OllamaService = Depends(get_ollama_service),
) -> Union[GenerateResponse, StreamingResponse]:
    """
    Endpoint to generate text based on a prompt using the specified model.

    This endpoint takes a prompt and model name, then returns a generated response from the
    Ollama model. It supports both streaming and non-streaming responses.
    """
    try:
        return await ollama_service.generate_response(
            prompt=request.prompt,
            model_name=request.model_name,
            stream=request.stream,
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
