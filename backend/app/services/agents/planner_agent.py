"""
Planner Agent and deterministic execution-plan builder.
"""

from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.core.logger import get_logger
from app.services.agents.base import BaseAgent
from app.services.orchestrator.planning import (
    ExecutionPlan,
    make_agent_step,
    make_plan,
    make_system_step,
)

OrchestratorContext = dict[str, Any]
logger = get_logger(__name__)

_DEFAULT_PHASES = [
    ("Define scope", "Clarify requirements, constraints, and success criteria"),
    ("Research & gather context", "Collect relevant information and identify dependencies"),
    ("Design the approach", "Choose a strategy, break into sub-tasks, assign priorities"),
    ("Execute incrementally", "Implement in small, verifiable steps and validate each"),
    ("Review & iterate", "Test outcomes against success criteria and adjust as needed"),
    ("Document & handoff", "Record decisions, outputs, and next actions"),
]

_ESCALATION_HINTS = {
    "escalate", "urgent", "critical", "legal", "security", "refund",
    "fraud", "breach", "manager", "angry", "complaint", "human",
}


@dataclass
class PlanningSnapshot:
    message: str
    lower_message: str
    selected_agent: str
    has_memory_summary: bool
    has_recent_messages: bool
    has_retrieval_results: bool
    has_retrieval_context: bool
    retrieval_quality: str
    has_request_history: bool
    has_conversation_history: bool
    memory_freshness: str
    summary_refresh_recommended: bool
    strong_escalation: bool


class PlannerAgent(BaseAgent):
    name = "planner"

    def create_execution_plan(self, ctx: OrchestratorContext) -> ExecutionPlan:
        snapshot = self._snapshot(ctx)

        if snapshot.strong_escalation:
            return self._plan_immediate_escalation(snapshot)

        if self._should_use_stored_summary(snapshot):
            system_step = make_system_step(
                "use_stored_summary",
                "Answer directly from the stored memory summary because it already satisfies the recap request",
                required_context=["memory_summary"],
            )
            skipped_step = make_agent_step(
                "summarizer",
                "Condense conversation context into a brief recap",
                required_context=["memory_summary", "recent_messages"],
                can_skip=True,
                skip_reason="Stored summary already satisfies the recap request",
                depends_on=[system_step.step_id],
            )
            return make_plan([system_step, skipped_step])

        if self._should_research_summarize_plan(snapshot):
            research_step = make_agent_step(
                "research",
                "Investigate the underlying findings or evidence",
                recommended_tools=self._recommended_research_tools(snapshot),
                required_context=["retrieval_context", "memory_summary"],
                can_skip=snapshot.retrieval_quality == "strong",
                skip_reason="Retrieval context is already strong enough for the downstream steps" if snapshot.retrieval_quality == "strong" else None,
            )
            summarizer_step = make_agent_step(
                "summarizer",
                "Condense the findings into a concise synthesis",
                recommended_tools=self._recommended_summarizer_tools(snapshot),
                required_context=["memory_summary", "recent_messages", "previous_step_output", "retrieval_context"],
                can_skip=snapshot.has_memory_summary and snapshot.memory_freshness == "fresh" and not snapshot.has_recent_messages,
                skip_reason="Stored summary already provides a concise recap" if snapshot.has_memory_summary and snapshot.memory_freshness == "fresh" and not snapshot.has_recent_messages else None,
                depends_on=[research_step.step_id],
            )
            planner_step = make_agent_step(
                "planner",
                "Turn the synthesized findings into concrete next steps",
                recommended_tools=self._recommended_planner_tools(snapshot),
                required_context=["retrieval_context", "memory_summary", "previous_step_output"],
                depends_on=[summarizer_step.step_id],
            )
            return make_plan([research_step, summarizer_step, planner_step])

        if self._should_investigate_then_escalate(snapshot):
            first_agent = "support" if self._is_support_issue(snapshot.lower_message) else "research"
            first_step = make_agent_step(
                first_agent,
                "Investigate the issue and gather supporting context",
                recommended_tools=self._recommended_support_tools(snapshot) if first_agent == "support" else self._recommended_research_tools(snapshot),
                required_context=["memory_summary", "recent_messages", "retrieval_context"],
                can_skip=first_agent == "research" and snapshot.retrieval_quality == "strong",
                skip_reason="Retrieval context is already strong enough for escalation review" if first_agent == "research" and snapshot.retrieval_quality == "strong" else None,
            )
            escalation_step = make_agent_step(
                "escalation",
                "Decide and communicate whether escalation is needed",
                recommended_tools=["trigger_escalation"],
                required_context=["memory_summary", "recent_messages", "previous_step_output"],
                depends_on=[first_step.step_id],
            )
            return make_plan([first_step, escalation_step])

        if self._should_research_then_plan(snapshot):
            research_step = make_agent_step(
                "research",
                "Analyze available documents and extract relevant findings",
                recommended_tools=self._recommended_research_tools(snapshot),
                required_context=["retrieval_context", "memory_summary"],
                can_skip=snapshot.retrieval_quality == "strong",
                skip_reason="Retrieval context already provides strong evidence for planning" if snapshot.retrieval_quality == "strong" else None,
            )
            planner_step = make_agent_step(
                "planner",
                "Convert the findings into an implementation roadmap",
                recommended_tools=self._recommended_planner_tools(snapshot),
                required_context=["retrieval_context", "memory_summary", "previous_step_output"],
                depends_on=[research_step.step_id],
            )
            return make_plan([research_step, planner_step])

        if self._should_plan_then_summarize(snapshot):
            planner_step = make_agent_step(
                "planner",
                "Create the detailed plan or roadmap",
                recommended_tools=self._recommended_planner_tools(snapshot),
                required_context=["retrieval_context", "memory_summary"],
            )
            summarizer_step = make_agent_step(
                "summarizer",
                "Condense the plan into a brief executive summary",
                required_context=["previous_step_output", "memory_summary"],
                can_skip=snapshot.has_memory_summary and snapshot.memory_freshness == "fresh" and "brief" in snapshot.lower_message,
                skip_reason="Existing summary already satisfies the brief recap intent" if snapshot.has_memory_summary and snapshot.memory_freshness == "fresh" and "brief" in snapshot.lower_message else None,
                depends_on=[planner_step.step_id],
            )
            return make_plan([planner_step, summarizer_step])

        return make_plan(
            [
                make_agent_step(
                    snapshot.selected_agent,
                    f"Handle the request with the {snapshot.selected_agent} agent",
                    recommended_tools=self._recommended_tools_for_agent(snapshot.selected_agent, snapshot),
                    required_context=self._required_context_for_agent(snapshot.selected_agent, snapshot),
                )
            ]
        )

    def _snapshot(self, ctx: OrchestratorContext) -> PlanningSnapshot:
        message = ctx["request"].message
        lower_message = message.lower()
        memory = ctx.get("memory", {})
        recent_messages = memory.get("recent_messages", [])
        request_history = getattr(ctx["request"], "history", []) or []

        return PlanningSnapshot(
            message=message,
            lower_message=lower_message,
            selected_agent=ctx["selected_agent"],
            has_memory_summary=bool(memory.get("summary_text")),
            has_recent_messages=bool(recent_messages),
            has_retrieval_results=bool(ctx.get("retrieval_results")),
            has_retrieval_context=bool(ctx.get("retrieval_context")),
            retrieval_quality=ctx.get("retrieval_quality", "none"),
            has_request_history=bool(request_history),
            has_conversation_history=bool(recent_messages or request_history),
            memory_freshness=memory.get("memory_freshness", "empty"),
            summary_refresh_recommended=bool(memory.get("summary_refresh_recommended", False)),
            strong_escalation=ctx["selected_agent"] == "escalation" or any(hint in lower_message for hint in _ESCALATION_HINTS),
        )

    def _plan_immediate_escalation(self, snapshot: PlanningSnapshot) -> ExecutionPlan:
        return make_plan(
            [
                make_agent_step(
                    "escalation",
                    "Immediately escalate because strong escalation signals are present",
                    recommended_tools=["trigger_escalation"],
                    required_context=["memory_summary", "recent_messages"],
                )
            ]
        )

    def _should_use_stored_summary(self, snapshot: PlanningSnapshot) -> bool:
        recap_terms = {"brief", "recap", "summary", "summarize", "tldr", "overview"}
        return (
            snapshot.has_memory_summary
            and snapshot.memory_freshness in {"fresh", "aging"}
            and not snapshot.summary_refresh_recommended
            and any(term in snapshot.lower_message for term in recap_terms)
            and "next step" not in snapshot.lower_message
            and "plan" not in snapshot.lower_message
        )

    def _should_research_summarize_plan(self, snapshot: PlanningSnapshot) -> bool:
        return (
            any(term in snapshot.lower_message for term in {"summarize", "summary", "tldr"})
            and any(term in snapshot.lower_message for term in {"next step", "next steps", "plan", "roadmap"})
            and any(term in snapshot.lower_message for term in {"finding", "findings", "analyze", "analysis", "research", "docs", "document"})
        )

    def _should_investigate_then_escalate(self, snapshot: PlanningSnapshot) -> bool:
        return (
            any(term in snapshot.lower_message for term in {"investigate", "look into", "analyze", "review"})
            and any(term in snapshot.lower_message for term in {"escalate", "escalation", "should be escalated"})
        )

    def _should_research_then_plan(self, snapshot: PlanningSnapshot) -> bool:
        return (
            any(term in snapshot.lower_message for term in {"roadmap", "implementation", "plan", "steps"})
            and any(term in snapshot.lower_message for term in {"analyze", "analysis", "docs", "document", "findings", "research", "architecture"})
        )

    def _should_plan_then_summarize(self, snapshot: PlanningSnapshot) -> bool:
        return (
            any(term in snapshot.lower_message for term in {"brief", "concise", "summary", "summarize"})
            and any(term in snapshot.lower_message for term in {"plan", "roadmap", "steps"})
        )

    def _is_support_issue(self, message: str) -> bool:
        return any(term in message for term in {"issue", "bug", "error", "problem", "login", "support", "customer"})

    def _recommended_research_tools(self, snapshot: PlanningSnapshot) -> list[str]:
        return ["search_knowledge_base"] if snapshot.retrieval_quality != "strong" else []

    def _recommended_support_tools(self, snapshot: PlanningSnapshot) -> list[str]:
        if snapshot.has_memory_summary or snapshot.has_recent_messages:
            return []
        if snapshot.has_conversation_history:
            return ["get_conversation_history"]
        return ["get_user_context"]

    def _recommended_summarizer_tools(self, snapshot: PlanningSnapshot) -> list[str]:
        return ["summarize_conversation"] if snapshot.has_recent_messages and (not snapshot.has_memory_summary or snapshot.summary_refresh_recommended) else []

    def _recommended_planner_tools(self, snapshot: PlanningSnapshot) -> list[str]:
        return ["search_knowledge_base"] if snapshot.retrieval_quality != "strong" else []

    def _recommended_tools_for_agent(self, agent_name: str, snapshot: PlanningSnapshot) -> list[str]:
        if agent_name == "research":
            return self._recommended_research_tools(snapshot)
        if agent_name == "support":
            return self._recommended_support_tools(snapshot)
        if agent_name == "summarizer":
            return self._recommended_summarizer_tools(snapshot)
        if agent_name == "planner":
            return self._recommended_planner_tools(snapshot)
        if agent_name == "escalation":
            return ["trigger_escalation"]
        return []

    def _required_context_for_agent(self, agent_name: str, snapshot: PlanningSnapshot) -> list[str]:
        if agent_name == "research":
            return ["retrieval_context", "memory_summary"]
        if agent_name == "support":
            return ["memory_summary", "recent_messages"]
        if agent_name == "summarizer":
            return ["memory_summary", "recent_messages", "retrieval_context"]
        if agent_name == "planner":
            return ["retrieval_context", "memory_summary"]
        if agent_name == "escalation":
            return ["memory_summary", "recent_messages"]
        return []

    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        self._log_run(ctx)

        message = ctx["request"].message
        retrieval_context: str = ctx.get("retrieval_context", "")
        retrieval_results: list = ctx.get("retrieval_results", [])
        memory: dict = ctx.get("memory", {})
        llm_used = False

        if not retrieval_results and not retrieval_context:
            tool_result = await self._call_tool(ctx, "search_knowledge_base", query=message)
            if tool_result:
                retrieval_context = tool_result["context"]

        if settings.openai_api_key:
            try:
                answer = await self._llm_answer(message, retrieval_context, memory)
                llm_used = True
            except Exception as exc:
                logger.warning("planner_agent.llm_failed", extra={"error": str(exc)})
                answer = self._deterministic_answer(message, retrieval_context, memory)
        else:
            answer = self._deterministic_answer(message, retrieval_context, memory)

        confidence = self._score_confidence(llm_used, retrieval_context, memory)
        reasoning = self._reasoning_summary(llm_used, retrieval_context, memory)

        result = self._build_result(
            answer=answer,
            confidence=confidence,
            ctx=ctx,
            reasoning_summary=reasoning,
        )
        ctx["answer"] = answer
        ctx["agent_result"] = result
        return ctx

    async def _llm_answer(self, message: str, retrieval_context: str, memory: dict) -> str:
        from app.services.llm.router import call_llm
        return await call_llm(
            agent_name="planner",
            message=message,
            retrieval_context=retrieval_context,
            memory=memory or None,
        )

    def _deterministic_answer(self, message: str, retrieval_context: str, memory: dict) -> str:
        steps = "\n".join(
            f"**Step {i+1}: {title}**\n   {detail}"
            for i, (title, detail) in enumerate(_DEFAULT_PHASES)
        )
        summary_text: str | None = memory.get("summary_text")

        context_note = ""
        if retrieval_context:
            context_note = (
                "\n\n**Reference material from knowledge base:**\n"
                f"{retrieval_context}\n"
                "Use this as background when executing the plan above."
            )
        elif summary_text:
            context_note = f"\n\n**Prior context:** {summary_text}"

        return (
            f"**Plan for:** \"{message}\"\n\n"
            f"{steps}"
            f"{context_note}\n\n"
            "_Tip: Share more details about your goal to receive a more tailored plan._"
        )

    def _score_confidence(self, llm_used: bool, retrieval_context: str, memory: dict) -> float:
        if retrieval_context:
            return 0.92 if llm_used else 0.85
        if memory.get("summary_text"):
            return 0.85 if llm_used else 0.75
        return 0.83 if llm_used else 0.7

    def _reasoning_summary(self, llm_used: bool, retrieval_context: str, memory: dict) -> str:
        path = "llm" if llm_used else "deterministic fallback"
        ctx_parts = []
        if retrieval_context:
            ctx_parts.append("retrieval context")
        if memory.get("summary_text"):
            ctx_parts.append("memory summary")
        ctx_str = ", ".join(ctx_parts) if ctx_parts else "no external context"
        return f"{path}; plan enriched with: {ctx_str}"


planner_agent = PlannerAgent()
