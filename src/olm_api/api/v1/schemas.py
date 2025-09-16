from typing import Optional

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    """Request schema for text generation endpoint."""

    prompt: str
    model_name: str
    stream: bool = False
    think: Optional[bool] = None


class GenerateResponse(BaseModel):
    """Response schema for text generation endpoint."""

    think: str = ""
    content: str = ""
    full_response: str
