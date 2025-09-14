from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from .message import Message
from .tool import ToolSchema


class ChatRequest(BaseModel):
    model: str = Field(alias="model_name", description="The name of the model to use")
    messages: List[Message]
    tools: Optional[List[ToolSchema]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    stream: bool = False
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    max_tokens: Optional[int] = None
    stop: Optional[Union[str, List[str]]] = None
    options: Optional[Dict[str, Any]] = None

    class Config:
        allow_population_by_field_name = True
