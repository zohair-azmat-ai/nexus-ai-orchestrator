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

from app.core.ids import get_correlation_id, get_trace_id
from app.core.logger import get_logger
from app.core.telemetry import record_latency, record_event
from app.schemas.chat import ChatRequest
from app.schemas.pipeline import PipelineResult
from app.services.events import logger as event_logger
from app.services.events.types import EVENT_STAGE_COMPLETED, EVENT_STAGE_FAILED, EVENT_STAGE_STARTED
from app.services.orchestrator.stages import (
    intake_stage,
    memory_stage,
    retrieval_stage,
    triage_stage,
    planning_stage,
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
    trace_id = get_trace_id() or correlation_id
    start = time.monotonic()

    ctx: OrchestratorContext = {
        "correlation_id": correlation_id,
        "trace_id": trace_id,
        "request": request,
        "db": db,
        "conversation_id": conversation_id,
        "memory": {},
        "retrieval_results": [],
        "retrieval_context": "",
        "selected_agent": "support",
        "execution_mode": "single_step",
        "final_agent": "support",
        "answer": "",
        "confidence": 0.0,
        "memory_used": False,
        "retrieval_used": False,
        "escalated": False,
        "events": [],
        "agent_result": None,
        "tools_used": [],
        "retrieval_quality": "none",
        "context_sources_used": [],
        "context_compaction_applied": False,
        "stage_timings": {},
        "execution_plan": None,
        "execution_plan_summary": None,
        "plan_summary": None,
        "executed_steps": [],
        "skipped_steps": [],
        "tools_planned": [],
    }

    pipeline = [
        intake_stage,
        memory_stage,
        retrieval_stage,
        triage_stage,
        planning_stage,
        response_stage,
        escalation_stage,
        event_log_stage,
    ]

    for stage in pipeline:
        stage_name = stage.__name__
        stage_key = stage_name.removesuffix("_stage")
        stage_start = time.monotonic()
        logger.info(f"orchestrator.stage.start", extra={"stage": stage_name, "correlation_id": correlation_id})
        event_logger.emit(
            EVENT_STAGE_STARTED,
            stage=stage_key,
            component="orchestrator",
            status="success",
        )
        try:
            ctx = await stage(ctx)
        except Exception as exc:
            stage_duration_ms = (time.monotonic() - stage_start) * 1000
            ctx["stage_timings"][stage_key] = round(stage_duration_ms, 2)
            logger.error(
                f"orchestrator.stage.error",
                extra={"stage": stage_name, "error": str(exc), "correlation_id": correlation_id},
            )
            event_logger.emit(
                EVENT_STAGE_FAILED,
                stage=stage_key,
                component="orchestrator",
                status="fail",
                latency_ms=round(stage_duration_ms, 2),
                error=str(exc),
            )
            ctx["answer"] = ctx.get("answer") or "I encountered an error processing your request."
            break
        stage_duration_ms = (time.monotonic() - stage_start) * 1000
        ctx["stage_timings"][stage_key] = round(stage_duration_ms, 2)
        event_logger.emit(
            EVENT_STAGE_COMPLETED,
            stage=stage_key,
            component="orchestrator",
            status="success",
            latency_ms=round(stage_duration_ms, 2),
        )
        logger.info(f"orchestrator.stage.done", extra={"stage": stage_name, "correlation_id": correlation_id})

    duration_ms = (time.monotonic() - start) * 1000
    record_latency("orchestrator.pipeline", duration_ms)
    record_event("orchestrator.complete", correlation_id=correlation_id, agent=ctx["selected_agent"])

    tools_used = ctx.get("tools_used", [])
    tools_planned = ctx.get("tools_planned", [])

    return PipelineResult(
        correlation_id=correlation_id,
        trace_id=trace_id,
        answer=ctx["answer"],
        selected_agent=ctx["selected_agent"],
        execution_mode=ctx.get("execution_mode", "single_step"),
        executed_steps_count=len(ctx.get("executed_steps", [])) or 1,
        skipped_steps_count=len(ctx.get("skipped_steps", [])),
        final_agent=ctx.get("final_agent", ctx["selected_agent"]),
        memory_used=ctx["memory_used"],
        retrieval_used=ctx["retrieval_used"],
        retrieval_context=ctx.get("retrieval_context", ""),
        retrieval_result_count=len(ctx.get("retrieval_results", [])),
        retrieval_quality=ctx.get("retrieval_quality", "none"),
        confidence=ctx.get("confidence", 0.0),
        memory_freshness=ctx.get("memory", {}).get("memory_freshness", "empty"),
        context_sources_used=ctx.get("context_sources_used", []),
        context_compaction_applied=ctx.get("context_compaction_applied", False),
        tools_planned=tools_planned,
        tools_used=tools_used,
        stage_timings=ctx.get("stage_timings", {}),
        plan_summary=ctx.get("plan_summary"),
        execution_plan_summary=ctx.get("execution_plan_summary"),
        event_summary={
            "stage_events": ctx["events"],
            "stage_timings": ctx.get("stage_timings", {}),
            "escalated": ctx["escalated"],
            "duration_ms": round(duration_ms, 2),
            "retrieval_results": len(ctx.get("retrieval_results", [])),
            "retrieval_quality": ctx.get("retrieval_quality", "none"),
            "memory_freshness": ctx.get("memory", {}).get("memory_freshness", "empty"),
            "agent": ctx["selected_agent"],
            "final_agent": ctx.get("final_agent", ctx["selected_agent"]),
            "confidence": ctx.get("confidence", 0.0),
            "context_sources_used": ctx.get("context_sources_used", []),
            "context_compaction_applied": ctx.get("context_compaction_applied", False),
            "tools_planned": tools_planned,
            "tools_used": tools_used,
            "trace_id": trace_id,
            "execution_mode": ctx.get("execution_mode", "single_step"),
            "executed_steps_count": len(ctx.get("executed_steps", [])) or 1,
            "skipped_steps_count": len(ctx.get("skipped_steps", [])),
        },
    )
