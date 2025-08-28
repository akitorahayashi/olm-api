from fastapi import APIRouter, Depends

from src.api.v1.schemas import GenerateRequest
from src.api.v1.services.ollama_service import OllamaService, get_ollama_service

router = APIRouter(
    prefix="/api/v1",
    tags=["generate"],
)


@router.post("/generate")
async def generate(
    request: GenerateRequest,
    ollama_service: OllamaService = Depends(get_ollama_service),
):
    """
    Endpoint to generate text based on a prompt using the specified model.

    This endpoint takes a prompt and model name, then returns a generated response from the
    Ollama model. It supports both streaming and non-streaming responses.
    """
    return await ollama_service.generate_response(
        prompt=request.prompt,
        model_name=request.model_name,
        stream=request.stream,
    )
