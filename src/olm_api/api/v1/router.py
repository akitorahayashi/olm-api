from typing import Union

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from .ollama_service_v1 import OllamaServiceV1
from .schemas import GenerateRequest, GenerateResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["chat"],
)


@router.post("/chat", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    ollama_service: OllamaServiceV1 = Depends(OllamaServiceV1.get_instance),
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
            think=request.think,
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        import logging
        import traceback

        logging.error(f"Unexpected error in generate endpoint: {e}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
