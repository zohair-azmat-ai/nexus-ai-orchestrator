"""
Internal pipeline result — returned by the orchestrator engine.

This is NOT an API schema. It carries only what the orchestration pipeline
produces. The chat route is responsible for enriching it with DB-layer fields
(conversation_id, messages_count) before returning the public ChatResponse.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineResult:
    correlation_id: str
    answer: str
    selected_agent: str
    memory_used: bool
    retrieval_used: bool
    event_summary: dict[str, Any] = field(default_factory=dict)
