from pydantic import BaseModel


class GenerateRequest(BaseModel):
    """Request schema for text generation endpoint."""

    prompt: str
    model_name: str
    stream: bool = False


class GenerateResponse(BaseModel):
    """Response schema for text generation endpoint."""

    response: str
