from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

import ollama
from src.config.state import app_state
from src.dependencies.common import get_ollama_client
from src.services.ollama import delete_model, list_models, pull_model

router = APIRouter(
    prefix="/api/v1/models",
    tags=["models"],
)


class PullRequest(BaseModel):
    name: str


@router.get("/", summary="List locally available models")
async def get_models(
    ollama_client: ollama.Client = Depends(get_ollama_client),
) -> Any:
    """
    Get a list of models that are available locally through Ollama.
    """
    return await list_models(ollama_client)


@router.post("/pull", summary="Pull a model from the Ollama registry")
async def pull_new_model(
    request: PullRequest,
    ollama_client: ollama.Client = Depends(get_ollama_client),
) -> Any:
    """
    Pull a new model from the official Ollama registry.
    """
    return await pull_model(request.name, ollama_client)


@router.delete(
    "/{model_name:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a local model",
)
async def remove_model(
    model_name: str,
    ollama_client: ollama.Client = Depends(get_ollama_client),
):
    """
    Delete a model from the local Ollama storage.
    """
    await delete_model(model_name, ollama_client)
    return None


@router.post("/switch/{model_name:path}", summary="Switch the active generation model")
async def switch_active_model(
    model_name: str,
    ollama_client: ollama.Client = Depends(get_ollama_client),
):
    """
    Switch the model used for the `/api/v1/generate` endpoint.
    The model must be available locally.
    """
    # Verify the model exists locally
    local_models = await list_models(ollama_client)
    if not any(m["name"] == model_name for m in local_models["models"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' not found locally. Please pull it first.",
        )

    # Set the model in the app state
    app_state.set_current_model(model_name)
    return {"message": f"Switched active model to {model_name}"}
