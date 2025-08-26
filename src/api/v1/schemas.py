from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LogRead(BaseModel):
    id: int
    timestamp: datetime
    client_host: Optional[str] = None
    request_method: Optional[str] = None
    request_path: Optional[str] = None
    response_status_code: Optional[int] = None
    prompt: Optional[str] = None
    generated_response: Optional[str] = None
    error_details: Optional[str] = None

    class Config:
        from_attributes = True


class GenerateRequest(BaseModel):
    prompt: str
    stream: bool = False


class GenerateResponse(BaseModel):
    response: str
