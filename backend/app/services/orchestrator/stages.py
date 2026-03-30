"""
Individual pipeline stage functions.

Each stage receives and returns the OrchestratorContext dict.
Stages are kept thin — they delegate to the appropriate service layer.
"""

from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

OrchestratorContext = dict[str, Any]


async def intake_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    """Validate, normalize, and enrich the incoming request."""
    request = ctx["request"]
    ctx["events"].append({"stage": "intake", "user_id": request.user_id, "session_id": request.session_id})
    logger.info("intake.processed", extra={"user_id": request.user_id, "session_id": request.session_id})
    return ctx


async def memory_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    """Load conversation history and user context from the memory layer."""
    request = ctx["request"]
    ctx["memory"] = {
        "history": request.history,
        "summary": None,
    }
    if request.history:
        ctx["memory_used"] = True
    ctx["events"].append({"stage": "memory", "history_turns": len(request.history)})
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

    if any(kw in message for kw in ["escalate", "urgent", "critical", "human"]):
        ctx["selected_agent"] = "escalation"
    elif any(kw in message for kw in ["summarize", "summary", "tldr"]):
        ctx["selected_agent"] = "summarizer"
    elif any(kw in message for kw in ["research", "find", "search", "what is"]):
        ctx["selected_agent"] = "research"
    elif any(kw in message for kw in ["plan", "roadmap", "steps", "how to"]):
        ctx["selected_agent"] = "planner"
    else:
        ctx["selected_agent"] = "support"

    ctx["events"].append({"stage": "triage", "agent": ctx["selected_agent"]})
    return ctx


async def response_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    """Generate the final answer using the selected agent."""
    # Phase 3: delegate to real agent.run(ctx) with LLM call.
    agent = ctx["selected_agent"]
    message = ctx["request"].message
    retrieval_context = ctx.get("retrieval_context", "")

    if retrieval_context:
        ctx["answer"] = (
            f"[{agent.upper()} AGENT] I found relevant context for your query.\n\n"
            f"{retrieval_context}\n\n"
            f"Phase 3 will generate a refined LLM response using this context."
        )
    else:
        ctx["answer"] = (
            f"[{agent.upper()} AGENT] Nexus AI received your message: \"{message}\". "
            "LLM integration is enabled in Phase 3. "
            "This is a Phase 2 scaffold response."
        )

    ctx["events"].append({"stage": "response", "agent": agent, "answer_length": len(ctx["answer"])})
    return ctx


async def escalation_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    """Apply escalation rules if required."""
    if ctx["selected_agent"] == "escalation":
        ctx["escalated"] = True
        ctx["events"].append({"stage": "escalation", "escalated": True})
    return ctx


async def event_log_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    """Persist a structured event record for this request."""
    logger.info(
        "event.log",
        extra={
            "correlation_id": ctx["correlation_id"],
            "user_id": ctx["request"].user_id,
            "agent": ctx["selected_agent"],
            "memory_used": ctx["memory_used"],
            "retrieval_used": ctx["retrieval_used"],
            "retrieval_results": len(ctx.get("retrieval_results", [])),
            "escalated": ctx["escalated"],
            "event_count": len(ctx["events"]),
        },
    )
    return ctx
