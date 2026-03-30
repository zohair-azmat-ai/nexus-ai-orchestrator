from pydantic import BaseModel, Field
from typing import Any


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the end user")
    session_id: str = Field(..., description="Conversation session identifier")
    message: str = Field(..., min_length=1, max_length=8192)
    history: list[ChatMessage] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    correlation_id: str
    answer: str
    selected_agent: str
    memory_used: bool
    retrieval_used: bool
    event_summary: dict[str, Any] = Field(default_factory=dict)
