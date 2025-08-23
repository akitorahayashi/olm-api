import ollama
from fastapi import APIRouter, Depends

from src.config.settings import Settings
from src.dependencies.common import get_ollama_client, get_settings
from src.schemas.generate import GenerateRequest
from src.services.ollama import generate_ollama_response

router = APIRouter(
    prefix="/api/v1",
    tags=["generate"],
)


@router.post("/generate")
async def generate(
    request: GenerateRequest,
    settings: Settings = Depends(get_settings),
    ollama_client: ollama.Client = Depends(get_ollama_client),
):
    """
    Endpoint to generate text based on a prompt.

    This endpoint takes a prompt and returns a generated response from the
    Ollama model. It supports both streaming and non-streaming responses.
    The core logic is delegated to the `generate_ollama_response` service.
    """
    return await generate_ollama_response(
        prompt=request.prompt,
        stream=request.stream,
        ollama_client=ollama_client,
        settings=settings,
    )
