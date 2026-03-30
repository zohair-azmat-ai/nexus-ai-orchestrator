"""
Orchestrator Engine — the central pipeline that processes every chat request.

Stages (in order):
  1. intake      — validate and enrich the incoming request
  2. memory      — load conversation context from memory layer
  3. retrieval   — semantic search for relevant documents
  4. triage      — select the appropriate agent
  5. response    — generate the LLM response via the selected agent
  6. escalation  — apply escalation rules if needed
  7. event_log   — persist a structured event record

Each stage receives and mutates a shared OrchestratorContext dict.
"""

import time
from typing import Any

from app.core.ids import get_correlation_id
from app.core.logger import get_logger
from app.core.telemetry import record_latency, record_event
from app.schemas.chat import ChatRequest
from app.schemas.pipeline import PipelineResult
from app.services.orchestrator.stages import (
    intake_stage,
    memory_stage,
    retrieval_stage,
    triage_stage,
    response_stage,
    escalation_stage,
    event_log_stage,
)

logger = get_logger(__name__)

OrchestratorContext = dict[str, Any]


async def run_pipeline(
    request: ChatRequest,
    db: "Any | None" = None,
    conversation_id: str | None = None,
) -> PipelineResult:
    """Execute the full orchestration pipeline and return a ChatResponse."""

    correlation_id = get_correlation_id()
    start = time.monotonic()

    ctx: OrchestratorContext = {
        "correlation_id": correlation_id,
        "request": request,
        "db": db,
        "conversation_id": conversation_id,
        "memory": {},
        "retrieval_results": [],
        "retrieval_context": "",
        "selected_agent": "support",
        "answer": "",
        "confidence": 0.0,
        "memory_used": False,
        "retrieval_used": False,
        "escalated": False,
        "events": [],
        "agent_result": None,
    }

    pipeline = [
        intake_stage,
        memory_stage,
        retrieval_stage,
        triage_stage,
        response_stage,
        escalation_stage,
        event_log_stage,
    ]

    for stage in pipeline:
        stage_name = stage.__name__
        logger.info(f"orchestrator.stage.start", extra={"stage": stage_name, "correlation_id": correlation_id})
        try:
            ctx = await stage(ctx)
        except Exception as exc:
            logger.error(
                f"orchestrator.stage.error",
                extra={"stage": stage_name, "error": str(exc), "correlation_id": correlation_id},
            )
            ctx["answer"] = ctx.get("answer") or "I encountered an error processing your request."
            break
        logger.info(f"orchestrator.stage.done", extra={"stage": stage_name, "correlation_id": correlation_id})

    duration_ms = (time.monotonic() - start) * 1000
    record_latency("orchestrator.pipeline", duration_ms)
    record_event("orchestrator.complete", correlation_id=correlation_id, agent=ctx["selected_agent"])

    return PipelineResult(
        correlation_id=correlation_id,
        answer=ctx["answer"],
        selected_agent=ctx["selected_agent"],
        memory_used=ctx["memory_used"],
        retrieval_used=ctx["retrieval_used"],
        retrieval_context=ctx.get("retrieval_context", ""),
        retrieval_result_count=len(ctx.get("retrieval_results", [])),
        confidence=ctx.get("confidence", 0.0),
        event_summary={
            "stage_events": ctx["events"],
            "escalated": ctx["escalated"],
            "duration_ms": round(duration_ms, 2),
            "retrieval_results": len(ctx.get("retrieval_results", [])),
            "agent": ctx["selected_agent"],
            "confidence": ctx.get("confidence", 0.0),
        },
    )
