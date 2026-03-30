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
    # Optional: supply an existing conversation ID to continue a session.
    # If omitted or not found, a new conversation is created.
    conversation_id: str | None = Field(default=None, description="Existing conversation ID to continue")


class ChatResponse(BaseModel):
    correlation_id: str
    answer: str
    selected_agent: str
    memory_used: bool
    retrieval_used: bool
    retrieval_result_count: int = 0
    conversation_id: str
    messages_count: int
    event_summary: dict[str, Any] = Field(default_factory=dict)
