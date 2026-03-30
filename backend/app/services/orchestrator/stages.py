"""
Individual pipeline stage functions.

Each stage receives and returns the shared orchestrator context dict.
"""

import time
from typing import Any

from app.core.logger import get_logger
from app.services.events import logger as event_logger
from app.services.events.types import EVENT_AGENT_EXECUTED, EVENT_AGENT_SELECTED

logger = get_logger(__name__)

OrchestratorContext = dict[str, Any]

_ESCALATION_KW = {
    "escalate", "urgent", "critical", "human", "angry", "legal", "refund",
    "security", "frustrated", "sue", "lawyer", "complaint", "unacceptable",
    "fraud", "breach", "manager",
}
_SUMMARIZER_KW = {
    "summarize", "summary", "tldr", "tl;dr", "brief", "shorten",
    "recap", "condense", "overview",
}
_RESEARCH_KW = {
    "research", "explain", "analyze", "compare", "what is", "why",
    "how does", "tell me about", "describe", "find out", "look up",
    "investigate", "explore",
}
_PLANNER_KW = {
    "plan", "roadmap", "steps", "how to", "strategy", "build",
    "implement", "design", "schedule", "milestone", "create a",
    "set up", "architecture",
}


def _matches(message: str, keywords: set[str]) -> bool:
    return any(kw in message for kw in keywords)


def _append_stage_event(ctx: OrchestratorContext, stage: str, **payload: Any) -> None:
    ctx["events"].append({"stage": stage, **payload})


async def intake_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    request = ctx["request"]
    _append_stage_event(ctx, "intake", user_id=request.user_id, session_id=request.session_id)
    logger.info("intake.processed", extra={"user_id": request.user_id, "session_id": request.session_id})
    return ctx


async def memory_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    from app.services.memory.manager import memory_manager

    request = ctx["request"]
    db = ctx.get("db")
    conversation_id = ctx.get("conversation_id")

    if db and conversation_id:
        try:
            mem = await memory_manager.load(
                db=db,
                conversation_id=conversation_id,
                user_id=request.user_id,
            )
            ctx["memory"] = mem
            ctx["memory_used"] = mem["memory_used"]
        except Exception as exc:
            logger.warning("memory_stage.failed", extra={"error": str(exc)})
            ctx["memory"] = {"history": request.history, "summary": None}
            ctx["memory_used"] = bool(request.history)
    else:
        ctx["memory"] = {"history": request.history, "summary": None}
        ctx["memory_used"] = bool(request.history)

    _append_stage_event(
        ctx,
        "memory",
        memory_used=ctx["memory_used"],
        memory_source=ctx["memory"].get("memory_source", "request"),
    )
    return ctx


async def retrieval_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    from app.services.retrieval.search import semantic_search

    message = ctx["request"].message

    try:
        results = await semantic_search.search(message)
    except Exception as exc:
        logger.warning(
            "retrieval_stage.failed",
            extra={"error": str(exc), "correlation_id": ctx.get("correlation_id", "")},
        )
        results = []

    ctx["retrieval_results"] = results
    ctx["retrieval_used"] = len(results) > 0
    ctx["retrieval_context"] = semantic_search.format_context(results) if results else ""

    _append_stage_event(
        ctx,
        "retrieval",
        results=len(results),
        retrieval_used=ctx["retrieval_used"],
    )
    return ctx


async def triage_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    message = ctx["request"].message.lower()

    if _matches(message, _ESCALATION_KW):
        ctx["selected_agent"] = "escalation"
    elif _matches(message, _SUMMARIZER_KW):
        ctx["selected_agent"] = "summarizer"
    elif _matches(message, _PLANNER_KW):
        ctx["selected_agent"] = "planner"
    elif _matches(message, _RESEARCH_KW):
        ctx["selected_agent"] = "research"
    else:
        ctx["selected_agent"] = "support"

    _append_stage_event(ctx, "triage", agent=ctx["selected_agent"])
    logger.info(
        "agent.selected",
        extra={
            "agent": ctx["selected_agent"],
            "correlation_id": ctx.get("correlation_id", ""),
            "user_id": ctx["request"].user_id,
        },
    )
    event_logger.emit(
        EVENT_AGENT_SELECTED,
        stage="agent",
        component=ctx["selected_agent"],
        status="success",
        user_id=ctx["request"].user_id,
    )
    return ctx


async def response_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    from app.services.agents import AGENT_REGISTRY

    agent_name = ctx["selected_agent"]
    agent = AGENT_REGISTRY.get(agent_name)

    if agent is None:
        logger.error(
            "response_stage.unknown_agent",
            extra={"agent": agent_name, "correlation_id": ctx.get("correlation_id", "")},
        )
        ctx["answer"] = "I encountered an internal error selecting the appropriate agent."
        ctx["confidence"] = 0.0
        _append_stage_event(ctx, "response", agent=agent_name, error="unknown agent")
        return ctx

    start = time.monotonic()
    ctx = await agent.run(ctx)
    latency_ms = (time.monotonic() - start) * 1000

    agent_result = ctx.get("agent_result")
    ctx["confidence"] = agent_result.confidence if agent_result else 0.0

    _append_stage_event(
        ctx,
        "response",
        agent=agent_name,
        answer_length=len(ctx.get("answer", "")),
        confidence=ctx["confidence"],
        latency_ms=round(latency_ms, 2),
    )
    logger.info(
        "agent.executed",
        extra={
            "agent": agent_name,
            "confidence": ctx["confidence"],
            "correlation_id": ctx.get("correlation_id", ""),
        },
    )
    event_logger.emit(
        EVENT_AGENT_EXECUTED,
        stage="agent",
        component=agent_name,
        status="success",
        latency_ms=round(latency_ms, 2),
        confidence=ctx["confidence"],
        used_memory=bool(agent_result.used_memory) if agent_result else False,
        used_retrieval=bool(agent_result.used_retrieval) if agent_result else False,
    )
    return ctx


async def escalation_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    agent_result = ctx.get("agent_result")
    agent_requires_escalation = agent_result is not None and agent_result.escalation_required

    if ctx["selected_agent"] == "escalation" or agent_requires_escalation:
        ctx["escalated"] = True
        _append_stage_event(ctx, "escalation", escalated=True)
        logger.info(
            "escalation.triggered",
            extra={
                "agent": ctx["selected_agent"],
                "correlation_id": ctx.get("correlation_id", ""),
                "user_id": ctx["request"].user_id,
            },
        )
    return ctx


async def event_log_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    logger.info(
        "event.log",
        extra={
            "correlation_id": ctx["correlation_id"],
            "trace_id": ctx.get("trace_id", ctx["correlation_id"]),
            "user_id": ctx["request"].user_id,
            "agent": ctx["selected_agent"],
            "confidence": ctx.get("confidence", 0.0),
            "memory_used": ctx["memory_used"],
            "retrieval_used": ctx["retrieval_used"],
            "retrieval_results": len(ctx.get("retrieval_results", [])),
            "escalated": ctx["escalated"],
            "tools_used": ctx.get("tools_used", []),
            "event_count": len(ctx["events"]),
            "stage_timings": ctx.get("stage_timings", {}),
        },
    )
    return ctx
