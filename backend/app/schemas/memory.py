from pydantic import BaseModel
from typing import Any


class MemoryEntry(BaseModel):
    role: str
    content: str
    timestamp: str | None = None


class MemoryResponse(BaseModel):
    user_id: str
    session_count: int
    short_term: list[MemoryEntry] = []
    long_term_summary: str | None = None
    metadata: dict[str, Any] = {}
