from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from .message import Message
from .tool import ToolSchema


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model: str = Field(alias="model_name", description="The name of the model to use")
    messages: List[Message] = Field(
        min_length=1, description="List of messages (must not be empty)"
    )
    tools: Optional[List[ToolSchema]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    stream: bool = False
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    max_tokens: Optional[int] = None
    stop: Optional[Union[str, List[str]]] = None
    options: Optional[Dict[str, Any]] = None
