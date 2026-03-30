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
    trace_id: str | None = None
    answer: str
    selected_agent: str
    execution_mode: str = "single_step"
    executed_steps_count: int = 1
    skipped_steps_count: int = 0
    final_agent: str = ""
    memory_used: bool
    retrieval_used: bool
    retrieval_result_count: int = 0
    retrieval_quality: str = "none"
    confidence: float = 0.0
    escalation_case_id: str | None = None
    escalation_status: str | None = None
    memory_freshness: str = "empty"
    context_sources_used: list[str] = Field(default_factory=list)
    context_compaction_applied: bool = False
    tools_planned: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    stage_timings: dict[str, float] = Field(default_factory=dict)
    plan_summary: dict[str, Any] | None = None
    execution_plan_summary: dict[str, Any] | None = None
    conversation_id: str
    messages_count: int
    event_summary: dict[str, Any] = Field(default_factory=dict)
