"""
Internal pipeline result — returned by the orchestrator engine.

This is NOT an API schema. It carries only what the orchestration pipeline
produces. The chat route enriches it with DB-layer fields
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
    retrieval_context: str = ""          # formatted context block (not exposed in answer)
    retrieval_result_count: int = 0      # how many chunks were retrieved
    confidence: float = 0.0              # agent confidence score (0.0 – 1.0)
    event_summary: dict[str, Any] = field(default_factory=dict)
