from typing import Dict, List, Optional

from pydantic import BaseModel

from .message import MessageRole
from .tool import ToolCall


class ChatResponseMessage(BaseModel):
    role: MessageRole
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class ChatResponseChoice(BaseModel):
    index: int
    message: ChatResponseMessage
    finish_reason: Optional[str] = None


class ChatResponse(BaseModel):
    id: Optional[str] = None
    object: str = "chat.completion"
    created: Optional[int] = None
    model: str
    choices: List[ChatResponseChoice]
    usage: Optional[Dict[str, int]] = None


class ChatStreamDelta(BaseModel):
    role: Optional[MessageRole] = None
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class ChatStreamChoice(BaseModel):
    index: int
    delta: ChatStreamDelta
    finish_reason: Optional[str] = None


class ChatStreamResponse(BaseModel):
    id: Optional[str] = None
    object: str = "chat.completion.chunk"
    created: Optional[int] = None
    model: str
    choices: List[ChatStreamChoice]
