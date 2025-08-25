from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.config.app_state import app_state
from src.services.ollama import OllamaService

router = APIRouter(
    prefix="/api/v1/models",
    tags=["models"],
)


class PullRequest(BaseModel):
    name: str


@router.get("/", summary="List locally available models")
async def get_models(
    ollama_service: OllamaService = Depends(OllamaService),
) -> Any:
    """
    Get a list of models that are available locally through Ollama.
    """
    return await ollama_service.list_models()


@router.post("/pull", summary="Pull a model from the Ollama registry")
async def pull_new_model(
    request: PullRequest,
    ollama_service: OllamaService = Depends(OllamaService),
) -> Any:
    """
    Pull a new model from the official Ollama registry.
    """
    return await ollama_service.pull_model(request.name)


@router.delete(
    "/{model_name:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a local model",
)
async def remove_model(
    model_name: str,
    ollama_service: OllamaService = Depends(OllamaService),
):
    """
    Delete a model from the local Ollama storage.
    """
    await ollama_service.delete_model(model_name)
    return None


@router.post("/switch/{model_name:path}", summary="Switch the active generation model")
async def switch_active_model(
    model_name: str,
    ollama_service: OllamaService = Depends(OllamaService),
):
    """
    Switch the model used for the `/api/v1/generate` endpoint.
    The model must be available locally.
    """
    # Verify the model exists locally
    local_models = await ollama_service.list_models()
    if not any(m["name"] == model_name for m in local_models["models"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' not found locally. Please pull it first.",
        )

    # Set the model in the app state
    app_state.set_current_model(model_name)
    return {"message": f"Switched active model to {model_name}"}
