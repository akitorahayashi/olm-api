from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class LogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    client_host: Optional[str] = None
    request_method: Optional[str] = None
    request_path: Optional[str] = None
    response_status_code: Optional[int] = None
    prompt: Optional[str] = None
    generated_response: Optional[str] = None
    error_details: Optional[str] = None


class GenerateRequest(BaseModel):
    prompt: str
    model_name: str
    stream: bool = False


class GenerateResponse(BaseModel):
    response: str
