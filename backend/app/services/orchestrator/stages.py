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
    EVENT_PLAN_CONTEXT_ROUTED,
    EVENT_PLAN_CREATED,
    EVENT_PLAN_STEP_COMPLETED,
    EVENT_PLAN_STEP_FAILED,
    EVENT_PLAN_STEP_SKIPPED,
    EVENT_PLAN_STEP_STARTED,
    EVENT_PLAN_TOOL_RECOMMENDED,
)
from app.services.orchestrator.planning import ExecutionPlan, ExecutionStep

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


def _summarize_text(text: str, limit: int = 220) -> str:
    compact = " ".join(text.split())
    return compact[:limit] + ("..." if len(compact) > limit else "")


def _compact_messages(messages: list[dict[str, Any]], limit: int = 4) -> list[dict[str, Any]]:
    return messages[:limit]


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
    ctx["base_retrieval_context"] = ctx["retrieval_context"]
    ctx["base_retrieval_results"] = list(results)
    ctx["base_memory"] = dict(ctx.get("memory", {}))

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
    )
    return ctx


async def escalation_stage(ctx: OrchestratorContext) -> OrchestratorContext:
    agent_result = ctx.get("agent_result")
    agent_requires_escalation = agent_result is not None and agent_result.escalation_required
    final_agent = ctx.get("final_agent", ctx["selected_agent"])

    if final_agent == "escalation" or agent_requires_escalation:
        ctx["escalated"] = True
        _append_stage_event(ctx, "escalation", escalated=True)
        logger.info(
            "escalation.triggered",
            extra={
                "agent": final_agent,
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
            "final_agent": ctx.get("final_agent", ctx["selected_agent"]),
            "confidence": ctx.get("confidence", 0.0),
            "memory_used": ctx["memory_used"],
            "retrieval_used": ctx["retrieval_used"],
            "retrieval_results": len(ctx.get("retrieval_results", [])),
            "escalated": ctx["escalated"],
            "tools_planned": ctx.get("tools_planned", []),
            "tools_used": ctx.get("tools_used", []),
            "event_count": len(ctx["events"]),
            "stage_timings": ctx.get("stage_timings", {}),
            "execution_mode": ctx.get("execution_mode", "single_step"),
            "executed_steps_count": len(ctx.get("executed_steps", [])) or 1,
            "skipped_steps_count": len(ctx.get("skipped_steps", [])),
        },
    )
    return ctx
