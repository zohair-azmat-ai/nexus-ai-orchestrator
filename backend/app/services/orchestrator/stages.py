"""
Individual pipeline stage functions.

Each stage receives and returns the shared orchestrator context dict.
"""

import time
from typing import Any

from app.core.logger import get_logger
from app.services.agents import AGENT_REGISTRY
from app.services.agents.planner_agent import planner_agent
from app.services.events import logger as event_logger
from app.services.events.types import (
    EVENT_AGENT_EXECUTED,
    EVENT_AGENT_SELECTED,
    EVENT_MEMORY_FRESHNESS_ASSESSED,
    EVENT_MEMORY_SUMMARY_REFRESH_RECOMMENDED,
    EVENT_PLAN_CONTEXT_ROUTED,
    EVENT_PLAN_CREATED,
    EVENT_PLAN_STEP_COMPLETED,
    EVENT_PLAN_STEP_FAILED,
    EVENT_PLAN_STEP_SKIPPED,
    EVENT_PLAN_STEP_STARTED,
    EVENT_PLAN_TOOL_RECOMMENDED,
    EVENT_RESPONSE_GROUNDING_MODE,
    EVENT_RETRIEVAL_CONTEXT_COMPACTED,
    EVENT_RETRIEVAL_QUALITY_ASSESSED,
)
from app.services.memory.freshness import assess_memory_freshness, select_recent_messages
from app.services.orchestrator.planning import ExecutionPlan, ExecutionStep
from app.services.retrieval.quality import assess_retrieval_quality

logger = get_logger(__name__)

OrchestratorContext = dict[str, Any]

_ESCALATION_KW = {
    "escalate", "urgent", "critical", "human", "angry", "legal", "refund",
    "security", "frustrated", "sue", "lawyer", "complaint", "unacceptable",
    "fraud", "breach", "manager",
    # frustration / dissatisfaction
    "terrible", "horrible", "awful", "ridiculous", "fed up", "fed-up",
    # cancellation intent
    "cancel", "cancellation", "cancel my", "want to cancel",
    # repeated-issue signals
    "not resolved", "still not", "third time", "again and again", "keep having",
    # urgency
    "immediately", "right now", "asap",
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


def _summarize_text(text: str, limit: int = 220) -> str:
    compact = " ".join(text.split())
    return compact[:limit] + ("..." if len(compact) > limit else "")


def _compact_messages(messages: list[dict[str, Any]], limit: int = 4) -> list[dict[str, Any]]:
    return messages[:limit]


def _is_simple_follow_up(message: str) -> bool:
    follow_up_terms = {
        "what did i just ask", "what were we discussing", "can you recap",
        "give me a recap", "follow up", "what next", "and then", "thanks",
        "thank you", "got it", "okay", "what do you mean by that",
    }
    return len(message.split()) <= 14 or any(term in message for term in follow_up_terms)


def _needs_external_evidence(message: str) -> bool:
    evidence_terms = {
        "docs", "document", "knowledge", "search", "find", "research", "analyze",
        "investigate", "architecture", "roadmap", "implementation", "evidence",
        "compare", "look up",
    }
    return any(term in message for term in evidence_terms)


def _should_skip_retrieval(ctx: OrchestratorContext) -> bool:
    message = ctx["request"].message.lower()
    memory = ctx.get("memory", {})
    memory_freshness = memory.get("memory_freshness", "empty")
    memory_sufficient = bool(memory.get("summary_text") or memory.get("recent_messages"))
    return (
        memory_sufficient
        and memory_freshness in {"fresh", "recent_only", "aging"}
        and _is_simple_follow_up(message)
        and not _needs_external_evidence(message)
    )


def _context_sources_used(ctx: OrchestratorContext) -> list[str]:
    sources: list[str] = []
    memory = ctx.get("memory", {})
    if memory.get("summary_text") or memory.get("recent_messages"):
        sources.append("memory")
    if ctx.get("retrieval_used"):
        sources.append("retrieval")
    if ctx.get("tools_used") or ctx.get("planned_tool_outputs"):
        sources.append("tools")
    if not sources:
        sources.append("request")
    return sources


def _apply_grounding_behavior(ctx: OrchestratorContext) -> None:
    retrieval_quality = ctx.get("retrieval_quality", "none")
    memory_freshness = ctx.get("memory", {}).get("memory_freshness", "empty")
    answer = ctx.get("answer", "")
    confidence = float(ctx.get("confidence", 0.0))
    agent_result = ctx.get("agent_result")
    llm_based = bool(agent_result and "llm" in str(getattr(agent_result, "reasoning_summary", "")).lower())

    if retrieval_quality == "strong":
        grounding_mode = "retrieval_strong"
        confidence = max(confidence, 0.82)
    elif retrieval_quality == "weak":
        grounding_mode = "retrieval_weak"
        confidence = min(confidence or 0.62, 0.68)
        cautious_prefix = "Based on limited retrieved evidence, here is a cautious assessment:\n\n"
        if answer and not answer.startswith("Based on limited retrieved evidence"):
            answer = f"{cautious_prefix}{answer}"
    elif ctx.get("memory_used"):
        grounding_mode = "memory_only"
        confidence = confidence if llm_based else min(confidence or 0.64, 0.72)
        if answer and not llm_based and not answer.startswith("Based on the available conversation context"):
            answer = f"Based on the available conversation context, here's the best answer I can give.\n\n{answer}"
    else:
        grounding_mode = "ungrounded"
        confidence = confidence if llm_based else min(confidence or 0.45, 0.5)
        note = "\n\nThis answer is based on the current request only and may need supporting documents for stronger grounding."
        if answer and not llm_based and "may need supporting documents for stronger grounding" not in answer:
            answer = f"{answer}{note}"

    if memory_freshness == "stale" and "summary may be missing recent details" not in answer:
        answer = f"{answer}\n\nNote: the stored conversation summary may be missing recent details."

    ctx["grounding_mode"] = grounding_mode
    ctx["answer"] = answer
    ctx["confidence"] = round(confidence, 2)

    event_logger.emit(
        EVENT_RESPONSE_GROUNDING_MODE,
        stage="response",
        component=ctx.get("final_agent", ctx.get("selected_agent", "support")),
        status="success",
        grounding_mode=grounding_mode,
        retrieval_quality=retrieval_quality,
        memory_freshness=memory_freshness,
    )


def _build_step_input_summary(ctx: OrchestratorContext, prior_outputs: list[dict[str, str]]) -> str:
    message = ctx["request"].message
    if not prior_outputs:
        return _summarize_text(message)
    latest = prior_outputs[-1]
    return _summarize_text(f"{message} | Prior output from {latest['target']}: {latest['answer']}")


def _dependency_statuses(ctx: OrchestratorContext) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for item in ctx.get("executed_steps", []):
        statuses[item["step_id"]] = item["status"]
    for item in ctx.get("skipped_steps", []):
        statuses[item["step_id"]] = item["status"]
    return statuses


def _dependencies_ready(ctx: OrchestratorContext, step: ExecutionStep) -> bool:
    statuses = _dependency_statuses(ctx)
    return all(statuses.get(dep) in {"completed", "skipped"} for dep in step.depends_on)


def _route_step_context(ctx: OrchestratorContext, step: ExecutionStep, prior_outputs: list[dict[str, str]]) -> None:
    base_retrieval_context = ctx.get("base_retrieval_context", "")
    base_retrieval_results = list(ctx.get("base_retrieval_results", []))
    base_memory = dict(ctx.get("base_memory", {}))
    required = set(step.required_context)

    routed_memory: dict[str, Any] = {}
    if "memory_summary" in required and base_memory.get("summary_text"):
        routed_memory["summary_text"] = base_memory["summary_text"]
    if "recent_messages" in required and base_memory.get("recent_messages"):
        routed_memory["recent_messages"] = _compact_messages(base_memory["recent_messages"])
    if routed_memory:
        routed_memory["memory_used"] = True
        routed_memory["memory_source"] = base_memory.get("memory_source", "db")
        routed_memory["memory_freshness"] = base_memory.get("memory_freshness", "empty")
        routed_memory["summary_refresh_recommended"] = base_memory.get("summary_refresh_recommended", False)
        routed_memory["messages_since_summary"] = base_memory.get("messages_since_summary", 0)
        routed_memory["context_compaction_applied"] = base_memory.get("context_compaction_applied", False)

    if "tool_outputs" in required and ctx.get("planned_tool_outputs"):
        routed_memory["planned_tool_outputs"] = dict(ctx["planned_tool_outputs"])

    retrieval_context_parts: list[str] = []
    if "retrieval_context" in required and base_retrieval_context:
        retrieval_context_parts.append(base_retrieval_context)

    if "previous_step_output" in required and prior_outputs:
        handoff = "\n\n".join(
            f"{item['target']} output:\n{_summarize_text(item['answer'], limit=320)}"
            for item in prior_outputs[-2:]
        )
        retrieval_context_parts.append(f"Previous execution outputs:\n{handoff}")
        existing_summary = routed_memory.get("summary_text")
        routed_memory["summary_text"] = (
            f"{existing_summary}\n\nPrevious execution outputs:\n{handoff}"
            if existing_summary else f"Previous execution outputs:\n{handoff}"
        )

    ctx["memory"] = routed_memory
    ctx["memory_used"] = bool(routed_memory)
    ctx["retrieval_context"] = "\n\n".join(part for part in retrieval_context_parts if part)
    ctx["retrieval_results"] = base_retrieval_results if "retrieval_context" in required else []
    ctx["retrieval_used"] = bool(ctx["retrieval_context"])
    ctx["planned_tool_hints"] = list(step.recommended_tools)

    event_logger.emit(
        EVENT_PLAN_CONTEXT_ROUTED,
        stage="plan",
        component=step.target,
        status="success",
        step_id=step.step_id,
        required_context=list(step.required_context),
    )


async def _execute_recommended_tools(ctx: OrchestratorContext, step: ExecutionStep) -> None:
    if not step.recommended_tools:
        return

    import app.services.tools  # noqa: F401

    from app.services.tools.registry import tool_registry

    for tool_name in step.recommended_tools:
        if tool_name != "search_knowledge_base":
            continue
        if ctx.get("retrieval_quality") == "strong":
            continue

        tool = tool_registry.get(tool_name)
        if tool is None:
            continue

        try:
            result = await tool.call(query=ctx["request"].message)
        except Exception as exc:
            logger.warning(
                "plan_tool_execution.failed",
                extra={"tool": tool_name, "step": step.step_id, "error": str(exc)},
            )
            continue
        ctx.setdefault("tools_used", []).append(tool_name)
        ctx.setdefault("planned_tool_outputs", {})[tool_name] = result

        assessment = assess_retrieval_quality(result.get("results", []))
        ctx["retrieval_results"] = assessment.compacted_results
        ctx["retrieval_context"] = assessment.compacted_context
        ctx["retrieval_used"] = bool(assessment.compacted_results)
        ctx["retrieval_quality"] = assessment.quality
        ctx["context_compaction_applied"] = (
            ctx.get("context_compaction_applied", False) or assessment.compaction_applied
        )
        ctx["retrieval_metadata"] = assessment.to_metadata()

        event_logger.emit(
            EVENT_RETRIEVAL_QUALITY_ASSESSED,
            stage="retrieval",
            component=tool_name,
            status="success",
            **assessment.to_metadata(),
        )
        if assessment.compaction_applied:
            event_logger.emit(
                EVENT_RETRIEVAL_CONTEXT_COMPACTED,
                stage="retrieval",
                component=tool_name,
                status="success",
                retained_results=len(assessment.compacted_results),
            )


def _execute_system_step(ctx: OrchestratorContext, step: ExecutionStep) -> None:
    if step.target == "use_stored_summary":
        summary_text = ctx.get("base_memory", {}).get("summary_text") or ctx.get("memory", {}).get("summary_text", "")
        ctx["answer"] = (
            f"**Stored Summary:**\n\n{summary_text}\n\n"
            "This existing summary already covers the requested recap, so no extra summarization step was needed."
        )
        ctx["confidence"] = 0.9 if summary_text else 0.4
        ctx["final_agent"] = "system"
        step.output_summary = _summarize_text(ctx["answer"])
        return
    raise RuntimeError(f"Unsupported system step target: {step.target}")


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
            if "memory_freshness" not in mem:
                derived_freshness = assess_memory_freshness(
                    summary_text=mem.get("summary_text"),
                    summary_version=mem.get("summary_version", 1 if mem.get("summary_text") else 0),
                    source_message_count=mem.get("source_message_count", mem.get("message_count", 0)),
                    total_message_count=mem.get("total_message_count", mem.get("message_count", 0)),
                    recent_messages=mem.get("recent_messages", []),
                    selected_recent_messages=mem.get("recent_messages", []),
                )
                mem = {
                    **mem,
                    "memory_freshness": derived_freshness.freshness,
                    "messages_since_summary": derived_freshness.messages_since_summary,
                    "high_signal_recent_count": derived_freshness.high_signal_recent_count,
                    "summary_refresh_recommended": derived_freshness.refresh_recommended,
                    "context_compaction_applied": mem.get("context_compaction_applied", False) or derived_freshness.compaction_applied,
                }
            ctx["memory"] = mem
            ctx["memory_used"] = mem["memory_used"]
        except Exception as exc:
            logger.warning("memory_stage.failed", extra={"error": str(exc)})
            selected_recent_messages, compacted = select_recent_messages(
                [{"role": item.role, "content": item.content} for item in request.history],
                limit=4,
            )
            freshness = assess_memory_freshness(
                summary_text=None,
                summary_version=0,
                source_message_count=0,
                total_message_count=len(request.history),
                recent_messages=[{"role": item.role, "content": item.content} for item in request.history],
                selected_recent_messages=selected_recent_messages,
            )
            ctx["memory"] = {
                "recent_messages": selected_recent_messages,
                "memory_source": "request",
                "memory_freshness": freshness.freshness,
                "summary_refresh_recommended": freshness.refresh_recommended,
                "context_compaction_applied": compacted or freshness.compaction_applied,
            }
            ctx["memory_used"] = bool(selected_recent_messages)
    else:
        raw_history = [{"role": item.role, "content": item.content} for item in request.history]
        selected_recent_messages, compacted = select_recent_messages(raw_history, limit=4)
        freshness = assess_memory_freshness(
            summary_text=None,
            summary_version=0,
            source_message_count=0,
            total_message_count=len(raw_history),
            recent_messages=raw_history,
            selected_recent_messages=selected_recent_messages,
        )
        ctx["memory"] = {
            "recent_messages": selected_recent_messages,
            "memory_source": "request",
            "memory_freshness": freshness.freshness,
            "summary_refresh_recommended": freshness.refresh_recommended,
            "context_compaction_applied": compacted or freshness.compaction_applied,
        }
        ctx["memory_used"] = bool(selected_recent_messages)

    ctx["context_compaction_applied"] = ctx.get("context_compaction_applied", False) or ctx["memory"].get(
        "context_compaction_applied", False
    )
    event_logger.emit(
        EVENT_MEMORY_FRESHNESS_ASSESSED,
        stage="memory",
        component=ctx["memory"].get("memory_source", "request"),
        status="success",
        memory_freshness=ctx["memory"].get("memory_freshness", "empty"),
        messages_since_summary=ctx["memory"].get("messages_since_summary", 0),
        summary_refresh_recommended=ctx["memory"].get("summary_refresh_recommended", False),
    )
    if ctx["memory"].get("summary_refresh_recommended"):
        event_logger.emit(
            EVENT_MEMORY_SUMMARY_REFRESH_RECOMMENDED,
            stage="memory",
            component=ctx["memory"].get("memory_source", "request"),
            status="success",
            memory_freshness=ctx["memory"].get("memory_freshness", "empty"),
        )

    _append_stage_event(
        ctx,
        "memory",
        memory_used=ctx["memory_used"],
        memory_source=ctx["memory"].get("memory_source", "request"),
        memory_freshness=ctx["memory"].get("memory_freshness", "empty"),
    )
    return ctx


async def retrieval_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    from app.services.retrieval.search import semantic_search

    message = ctx["request"].message

    if _should_skip_retrieval(ctx):
        results: list[dict[str, Any]] = []
        assessment = assess_retrieval_quality(results)
        ctx["retrieval_results"] = []
        ctx["retrieval_used"] = False
        ctx["retrieval_context"] = ""
        ctx["retrieval_quality"] = "none"
        ctx["retrieval_metadata"] = assessment.to_metadata()
        ctx["base_retrieval_context"] = ""
        ctx["base_retrieval_results"] = []
        ctx["base_memory"] = dict(ctx.get("memory", {}))
        event_logger.emit(
            EVENT_RETRIEVAL_QUALITY_ASSESSED,
            stage="retrieval",
            component="semantic_search",
            status="success",
            skipped=True,
            skip_reason="memory_sufficient",
            **assessment.to_metadata(),
        )
        _append_stage_event(
            ctx,
            "retrieval",
            results=0,
            retrieval_used=False,
            retrieval_quality="none",
            skipped=True,
        )
        return ctx

    try:
        results = await semantic_search.search(message)
    except Exception as exc:
        logger.warning(
            "retrieval_stage.failed",
            extra={"error": str(exc), "correlation_id": ctx.get("correlation_id", "")},
        )
        results = []

    assessment = assess_retrieval_quality(results)
    ctx["retrieval_results"] = assessment.compacted_results
    ctx["retrieval_used"] = len(assessment.compacted_results) > 0
    ctx["retrieval_context"] = assessment.compacted_context
    ctx["retrieval_quality"] = assessment.quality
    ctx["retrieval_metadata"] = assessment.to_metadata()
    ctx["base_retrieval_context"] = ctx["retrieval_context"]
    ctx["base_retrieval_results"] = list(assessment.compacted_results)
    ctx["base_memory"] = dict(ctx.get("memory", {}))
    ctx["context_compaction_applied"] = (
        ctx.get("context_compaction_applied", False) or assessment.compaction_applied
    )

    event_logger.emit(
        EVENT_RETRIEVAL_QUALITY_ASSESSED,
        stage="retrieval",
        component="semantic_search",
        status="success",
        **assessment.to_metadata(),
    )
    if assessment.compaction_applied:
        event_logger.emit(
            EVENT_RETRIEVAL_CONTEXT_COMPACTED,
            stage="retrieval",
            component="semantic_search",
            status="success",
            retained_results=len(assessment.compacted_results),
        )

    _append_stage_event(
        ctx,
        "retrieval",
        results=len(assessment.compacted_results),
        retrieval_used=ctx["retrieval_used"],
        retrieval_quality=assessment.quality,
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


async def planning_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    plan = planner_agent.create_execution_plan(ctx)
    ctx["execution_plan"] = plan
    ctx["execution_mode"] = plan.execution_mode
    ctx["executed_steps"] = []
    ctx["skipped_steps"] = []
    ctx["chain_outputs"] = []
    ctx["planned_tool_outputs"] = {}
    ctx["final_agent"] = ctx["selected_agent"]
    ctx["tools_planned"] = plan.tools_planned

    event_logger.emit(
        EVENT_PLAN_CREATED,
        stage="plan",
        component="planner",
        status="success",
        plan_id=plan.plan_id,
        execution_mode=plan.execution_mode,
        tools_planned=plan.tools_planned,
        steps=[step.to_dict() for step in plan.steps],
    )
    for step in plan.steps:
        for tool_name in step.recommended_tools:
            event_logger.emit(
                EVENT_PLAN_TOOL_RECOMMENDED,
                stage="plan",
                component=step.target,
                status="success",
                plan_id=plan.plan_id,
                step_id=step.step_id,
                tool_name=tool_name,
            )

    _append_stage_event(
        ctx,
        "planning",
        plan_id=plan.plan_id,
        execution_mode=plan.execution_mode,
        tools_planned=plan.tools_planned,
        steps=[step.target for step in plan.steps],
    )
    return ctx


async def _skip_step(ctx: OrchestratorContext, step: ExecutionStep) -> OrchestratorContext:
    step.status = "skipped"
    step.output_summary = step.skip_reason or "Step skipped"
    ctx["skipped_steps"].append(step.to_dict())
    event_logger.emit(
        EVENT_PLAN_STEP_SKIPPED,
        stage="plan",
        component=step.target,
        status="success",
        plan_id=ctx["execution_plan"].plan_id,
        step=step.to_dict(),
    )
    _append_stage_event(
        ctx,
        "plan_step",
        step_id=step.step_id,
        target=step.target,
        status=step.status,
        skip_reason=step.skip_reason,
    )
    return ctx


async def _run_step(ctx: OrchestratorContext, step: ExecutionStep) -> OrchestratorContext:
    if not _dependencies_ready(ctx, step):
        raise RuntimeError(f"Dependencies not satisfied for step {step.step_id}")

    prior_outputs = list(ctx.get("chain_outputs", []))
    _route_step_context(ctx, step, prior_outputs)
    step.input_summary = _build_step_input_summary(ctx, prior_outputs)

    if step.can_skip and step.skip_reason:
        return await _skip_step(ctx, step)

    step.status = "running"
    event_logger.emit(
        EVENT_PLAN_STEP_STARTED,
        stage="plan",
        component=step.target,
        status="running",
        plan_id=ctx["execution_plan"].plan_id,
        step=step.to_dict(),
    )

    start = time.monotonic()
    try:
        await _execute_recommended_tools(ctx, step)
        if step.type == "agent":
            agent = AGENT_REGISTRY.get(step.target)
            if agent is None:
                raise RuntimeError(f"Unknown agent in execution plan: {step.target}")
            ctx = await agent.run(ctx)
            agent_result = ctx.get("agent_result")
            ctx["confidence"] = agent_result.confidence if agent_result else 0.0
            ctx["final_agent"] = step.target
        elif step.type == "system":
            _execute_system_step(ctx, step)
        else:
            raise RuntimeError(f"Unsupported execution step type: {step.type}")
    except Exception as exc:
        latency_ms = (time.monotonic() - start) * 1000
        step.status = "failed"
        step.output_summary = str(exc)
        event_logger.emit(
            EVENT_PLAN_STEP_FAILED,
            stage="plan",
            component=step.target,
            status="fail",
            plan_id=ctx["execution_plan"].plan_id,
            latency_ms=round(latency_ms, 2),
            step=step.to_dict(),
            error=str(exc),
        )
        raise

    latency_ms = (time.monotonic() - start) * 1000
    step.status = "completed"
    if not step.output_summary:
        step.output_summary = _summarize_text(ctx.get("answer", ""))
    ctx["executed_steps"].append(step.to_dict())
    ctx["chain_outputs"].append({"target": step.target, "answer": ctx.get("answer", "")})

    _append_stage_event(
        ctx,
        "plan_step",
        step_id=step.step_id,
        target=step.target,
        status=step.status,
        latency_ms=round(latency_ms, 2),
    )
    if step.type == "agent":
        agent_result = ctx.get("agent_result")
        logger.info(
            "agent.executed",
            extra={
                "agent": step.target,
                "confidence": ctx.get("confidence", 0.0),
                "correlation_id": ctx.get("correlation_id", ""),
            },
        )
        event_logger.emit(
            EVENT_AGENT_EXECUTED,
            stage="agent",
            component=step.target,
            status="success",
            latency_ms=round(latency_ms, 2),
            confidence=ctx.get("confidence", 0.0),
            used_memory=bool(agent_result.used_memory) if agent_result else False,
            used_retrieval=bool(agent_result.used_retrieval) if agent_result else False,
            execution_mode=ctx.get("execution_mode", "single_step"),
            step_id=step.step_id,
        )
    event_logger.emit(
        EVENT_PLAN_STEP_COMPLETED,
        stage="plan",
        component=step.target,
        status="success",
        plan_id=ctx["execution_plan"].plan_id,
        latency_ms=round(latency_ms, 2),
        step=step.to_dict(),
    )
    return ctx


async def response_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    plan: ExecutionPlan = ctx["execution_plan"]

    for step in plan.steps:
        ctx = await _run_step(ctx, step)

    _apply_grounding_behavior(ctx)

    context_sources_used = _context_sources_used(ctx)
    ctx["context_sources_used"] = context_sources_used

    ctx["execution_plan_summary"] = {
        "plan_id": plan.plan_id,
        "execution_mode": plan.execution_mode,
        "tools_planned": plan.tools_planned,
        "steps": [step.to_dict() for step in plan.steps],
    }
    ctx["plan_summary"] = {
        "plan_id": plan.plan_id,
        "execution_mode": plan.execution_mode,
        "executed_steps_count": len(ctx.get("executed_steps", [])) or 1,
        "skipped_steps_count": len(ctx.get("skipped_steps", [])),
        "tools_planned": plan.tools_planned,
        "retrieval_quality": ctx.get("retrieval_quality", "none"),
        "memory_freshness": ctx.get("memory", {}).get("memory_freshness", "empty"),
        "context_sources_used": context_sources_used,
    }

    _append_stage_event(
        ctx,
        "response",
        agent=ctx.get("final_agent", ctx["selected_agent"]),
        answer_length=len(ctx.get("answer", "")),
        confidence=ctx.get("confidence", 0.0),
        executed_steps_count=len(ctx.get("executed_steps", [])) or 1,
        skipped_steps_count=len(ctx.get("skipped_steps", [])),
        execution_mode=plan.execution_mode,
        retrieval_quality=ctx.get("retrieval_quality", "none"),
        memory_freshness=ctx.get("memory", {}).get("memory_freshness", "empty"),
    )
    return ctx


async def escalation_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    agent_result = ctx.get("agent_result")
    agent_requires_escalation = agent_result is not None and agent_result.escalation_required
    final_agent = ctx.get("final_agent", ctx["selected_agent"])

    if final_agent == "escalation" or agent_requires_escalation:
        ctx["escalated"] = True
        db = ctx.get("db")
        conversation_id = ctx.get("conversation_id")
        existing_case_id = None
        existing_case_status = None
        if agent_result and isinstance(agent_result.notes, dict):
            existing_case_id = agent_result.notes.get("case_id")
            existing_case_status = agent_result.notes.get("status")

        if existing_case_id:
            ctx["escalation_case_id"] = existing_case_id
            ctx["escalation_status"] = existing_case_status or "open"
        elif db and conversation_id:
            from app.services.escalations.manager import escalation_workflow, infer_severity

            reason = "Escalation requested"
            if agent_result and isinstance(agent_result.notes, dict):
                reason = agent_result.notes.get("detected_reason") or agent_result.notes.get("reason") or reason
            latest_summary = ""
            if agent_result:
                latest_summary = agent_result.reasoning_summary or ctx.get("answer", "")
            case = await escalation_workflow.ensure_case(
                db,
                conversation_id=conversation_id,
                trace_id=ctx.get("trace_id"),
                user_id=ctx["request"].user_id,
                escalation_reason=reason,
                severity=infer_severity(reason),
                latest_agent=final_agent,
                latest_summary=latest_summary,
                note_author=final_agent or "system",
                note_type="agent" if final_agent else "system",
            )
            ctx["escalation_case_id"] = case.id
            ctx["escalation_status"] = case.status
        _append_stage_event(ctx, "escalation", escalated=True)
        logger.info(
            "escalation.triggered",
            extra={
                "agent": final_agent,
                "correlation_id": ctx.get("correlation_id", ""),
                "user_id": ctx["request"].user_id,
                "case_id": ctx.get("escalation_case_id"),
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
            "final_agent": ctx.get("final_agent", ctx["selected_agent"]),
            "confidence": ctx.get("confidence", 0.0),
            "memory_used": ctx["memory_used"],
            "retrieval_used": ctx["retrieval_used"],
            "retrieval_results": len(ctx.get("retrieval_results", [])),
            "retrieval_quality": ctx.get("retrieval_quality", "none"),
            "memory_freshness": ctx.get("memory", {}).get("memory_freshness", "empty"),
            "escalation_case_id": ctx.get("escalation_case_id"),
            "escalation_status": ctx.get("escalation_status"),
            "escalated": ctx["escalated"],
            "tools_planned": ctx.get("tools_planned", []),
            "tools_used": ctx.get("tools_used", []),
            "context_sources_used": ctx.get("context_sources_used", []),
            "context_compaction_applied": ctx.get("context_compaction_applied", False),
            "event_count": len(ctx["events"]),
            "stage_timings": ctx.get("stage_timings", {}),
            "execution_mode": ctx.get("execution_mode", "single_step"),
            "executed_steps_count": len(ctx.get("executed_steps", [])) or 1,
            "skipped_steps_count": len(ctx.get("skipped_steps", [])),
        },
    )
    return ctx
