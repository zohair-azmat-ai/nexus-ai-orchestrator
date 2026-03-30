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
    # Phase 1: stub — returns empty context
    # Phase 2: call MemoryManager.load(user_id, session_id)
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
    """Perform semantic retrieval from the vector store."""
    # Phase 1: stub — no real retrieval
    # Phase 2: call RetrievalService.search(query, top_k=5)
    ctx["retrieval_results"] = []
    ctx["retrieval_used"] = False
    ctx["events"].append({"stage": "retrieval", "results": 0})
    return ctx


async def triage_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    """Select the most appropriate agent for this request."""
    # Phase 1: simple keyword-based triage
    # Phase 3: LLM-based routing with intent classification
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
    # Phase 1: stub response — no real LLM call
    # Phase 3: delegate to agent.run(ctx)
    agent = ctx["selected_agent"]
    message = ctx["request"].message

    ctx["answer"] = (
        f"[{agent.upper()} AGENT] Nexus AI received your message: \"{message}\". "
        "LLM integration is enabled in Phase 3. "
        "This is a Phase 1 scaffold response."
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
    # Phase 1: log to structured logger
    # Phase 4: persist to event store table
    logger.info(
        "event.log",
        extra={
            "correlation_id": ctx["correlation_id"],
            "user_id": ctx["request"].user_id,
            "agent": ctx["selected_agent"],
            "memory_used": ctx["memory_used"],
            "retrieval_used": ctx["retrieval_used"],
            "escalated": ctx["escalated"],
            "event_count": len(ctx["events"]),
        },
    )
    return ctx
