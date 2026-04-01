from pydantic import BaseModel, Field
from typing import Any


class JobIngestRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw text content to ingest")
    source: str = Field(default="", description="Source label (e.g. 'docs', 'kb')")
    metadata: dict[str, Any] = Field(default_factory=dict)
    document_id: str | None = Field(default=None, description="Optional caller-supplied document ID")


class JobMemorySummaryRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation to summarize")
    user_id: str = Field(..., description="Owner of the conversation")


class JobResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str
    updated_at: str


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
