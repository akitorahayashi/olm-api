from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel


class ToolType(str, Enum):
    FUNCTION = "function"


class FunctionSchema(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class ToolSchema(BaseModel):
    type: ToolType
    function: FunctionSchema


class ToolCall(BaseModel):
    id: str
    type: str
    function: Dict[str, Any]
