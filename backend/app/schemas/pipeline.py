"""
Internal pipeline result returned by the orchestrator engine.

This is NOT an API schema. It carries only what the orchestration pipeline
produces. The chat route enriches it with DB-layer fields before returning the
public ChatResponse.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineResult:
    correlation_id: str
    trace_id: str
    answer: str
    selected_agent: str
    execution_mode: str
    executed_steps_count: int
    skipped_steps_count: int
    final_agent: str
    memory_used: bool
    retrieval_used: bool
    retrieval_context: str = ""
    retrieval_result_count: int = 0
    retrieval_quality: str = "none"
    confidence: float = 0.0
    memory_freshness: str = "empty"
    context_sources_used: list[str] = field(default_factory=list)
    context_compaction_applied: bool = False
    tools_planned: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    stage_timings: dict[str, float] = field(default_factory=dict)
    plan_summary: dict[str, Any] | None = None
    execution_plan_summary: dict[str, Any] | None = None
    event_summary: dict[str, Any] = field(default_factory=dict)
