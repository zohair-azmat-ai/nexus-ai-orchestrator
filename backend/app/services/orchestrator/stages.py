"""
Individual pipeline stage functions.

Each stage receives and returns the OrchestratorContext dict.
Stages are kept thin — they delegate to the appropriate service layer.
"""

from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

OrchestratorContext = dict[str, Any]

# ─── Keyword sets for deterministic triage ───────────────────────────────────
# Listed in priority order: escalation checked first, support last.

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


# ─── Pipeline stages ──────────────────────────────────────────────────────────

async def intake_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    """Validate, normalize, and enrich the incoming request."""
    request = ctx["request"]
    ctx["events"].append({"stage": "intake", "user_id": request.user_id, "session_id": request.session_id})
    logger.info("intake.processed", extra={"user_id": request.user_id, "session_id": request.session_id})
    return ctx


async def memory_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    """Load conversation history and user context from the DB memory layer."""
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
        # Fallback: use request history when no DB session available
        ctx["memory"] = {"history": request.history, "summary": None}
        ctx["memory_used"] = bool(request.history)

    ctx["events"].append({
        "stage": "memory",
        "memory_used": ctx["memory_used"],
        "memory_source": ctx["memory"].get("memory_source", "request"),
    })
    return ctx


async def retrieval_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    """
    Perform semantic retrieval from the vector store.

    On success, populates ctx["retrieval_results"] and ctx["retrieval_context"].
    On any failure (Qdrant down, missing API key), degrades gracefully to empty.
    """
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
    ctx["retrieval_context"] = (
        semantic_search.format_context(results) if results else ""
    )

    ctx["events"].append({
        "stage": "retrieval",
        "results": len(results),
        "retrieval_used": ctx["retrieval_used"],
    })
    return ctx


async def triage_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    """Select the most appropriate agent for this request."""
    message = ctx["request"].message.lower()

    # Priority: escalation > summarizer > planner > research > support
    # Planner checked before research because "what is the roadmap?" should
    # route to planner, not research (specific plan terms win over general query words).
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

    ctx["events"].append({"stage": "triage", "agent": ctx["selected_agent"]})
    logger.info(
        "agent.selected",
        extra={
            "agent": ctx["selected_agent"],
            "correlation_id": ctx.get("correlation_id", ""),
            "user_id": ctx["request"].user_id,
        },
    )
    return ctx


async def response_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    """Dispatch to the selected agent and populate ctx['answer']."""
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
        ctx["events"].append({"stage": "response", "agent": agent_name, "error": "unknown agent"})
        return ctx

    ctx = await agent.run(ctx)

    agent_result = ctx.get("agent_result")
    ctx["confidence"] = agent_result.confidence if agent_result else 0.0

    ctx["events"].append({
        "stage": "response",
        "agent": agent_name,
        "answer_length": len(ctx.get("answer", "")),
        "confidence": ctx["confidence"],
    })
    logger.info(
        "agent.executed",
        extra={
            "agent": agent_name,
            "confidence": ctx["confidence"],
            "correlation_id": ctx.get("correlation_id", ""),
        },
    )
    return ctx


async def escalation_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    """Apply escalation rules — respects agent escalation_required flag."""
    agent_result = ctx.get("agent_result")
    agent_requires_escalation = agent_result is not None and agent_result.escalation_required

    if ctx["selected_agent"] == "escalation" or agent_requires_escalation:
        ctx["escalated"] = True
        ctx["events"].append({"stage": "escalation", "escalated": True})
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
    """Persist a structured event record for this request."""
    logger.info(
        "event.log",
        extra={
            "correlation_id": ctx["correlation_id"],
            "user_id": ctx["request"].user_id,
            "agent": ctx["selected_agent"],
            "confidence": ctx.get("confidence", 0.0),
            "memory_used": ctx["memory_used"],
            "retrieval_used": ctx["retrieval_used"],
            "retrieval_results": len(ctx.get("retrieval_results", [])),
            "escalated": ctx["escalated"],
            "event_count": len(ctx["events"]),
        },
    )
    return ctx
