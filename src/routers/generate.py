from fastapi import APIRouter, Depends

from src.config.app_state import app_state
from src.schemas.generate import GenerateRequest
from src.services.ollama import OllamaService

router = APIRouter(
    prefix="/api/v1",
    tags=["generate"],
)


@router.post("/generate")
async def generate(
    request: GenerateRequest,
    ollama_service: OllamaService = Depends(OllamaService),
):
    """
    Endpoint to generate text based on a prompt using the currently active model.

    This endpoint takes a prompt and returns a generated response from the
    Ollama model. It supports both streaming and non-streaming responses.
    The core logic is delegated to the `generate_ollama_response` service.
    """
    # Get the currently active model from the application state
    active_model = app_state.get_current_model()

    return await ollama_service.generate_response(
        prompt=request.prompt,
        model_name=active_model,
        stream=request.stream,
    )
