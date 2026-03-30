"""
Planner Agent — decomposes goals into structured, actionable step-by-step plans.

LLM path: generates an intelligent, goal-specific plan using OpenAI.
Fallback: generic 6-phase plan template with context-aware enrichment.
"""

from typing import Any

from app.core.config import settings
from app.core.logger import get_logger
from app.services.agents.base import BaseAgent, AgentResult
from app.services.orchestrator.planning import ExecutionPlan, make_agent_step, make_plan

OrchestratorContext = dict[str, Any]
logger = get_logger(__name__)

_DEFAULT_PHASES = [
    ("Define scope", "Clarify requirements, constraints, and success criteria"),
    ("Research & gather context", "Collect relevant information and identify dependencies"),
    ("Design the approach", "Choose a strategy, break into sub-tasks, assign priorities"),
    ("Execute incrementally", "Implement in small, verifiable steps — validate each before proceeding"),
    ("Review & iterate", "Test outcomes against success criteria, adjust as needed"),
    ("Document & handoff", "Record decisions, outputs, and next actions"),
]


class PlannerAgent(BaseAgent):
    name = "planner"

    def create_execution_plan(self, ctx: OrchestratorContext) -> ExecutionPlan:
        message = ctx["request"].message.lower()
        selected_agent = ctx["selected_agent"]

        if self._should_research_summarize_plan(message):
            return make_plan(
                [
                    make_agent_step("research", "Investigate the underlying findings or evidence"),
                    make_agent_step("summarizer", "Condense the findings into a concise synthesis"),
                    make_agent_step("planner", "Turn the synthesized findings into concrete next steps"),
                ]
            )

        if self._should_investigate_then_escalate(message):
            first_agent = "support" if self._is_support_issue(message) else "research"
            return make_plan(
                [
                    make_agent_step(first_agent, "Investigate the issue and gather supporting context"),
                    make_agent_step("escalation", "Decide and communicate whether escalation is needed"),
                ]
            )

        if self._should_research_then_plan(message):
            return make_plan(
                [
                    make_agent_step("research", "Analyze available documents and extract relevant findings"),
                    make_agent_step("planner", "Convert the findings into an implementation roadmap"),
                ]
            )

        if self._should_plan_then_summarize(message):
            return make_plan(
                [
                    make_agent_step("planner", "Create the detailed plan or roadmap"),
                    make_agent_step("summarizer", "Condense the plan into a brief executive summary"),
                ]
            )

        return make_plan([make_agent_step(selected_agent, f"Handle the request with the {selected_agent} agent")])

    def _should_research_summarize_plan(self, message: str) -> bool:
        return (
            any(term in message for term in {"summarize", "summary", "tldr"})
            and any(term in message for term in {"next step", "next steps", "plan", "roadmap"})
            and any(term in message for term in {"finding", "findings", "analyze", "analysis", "research", "docs", "document"})
        )

    def _should_investigate_then_escalate(self, message: str) -> bool:
        return (
            any(term in message for term in {"investigate", "look into", "analyze", "review"})
            and any(term in message for term in {"escalate", "escalation", "should be escalated"})
        )

    def _should_research_then_plan(self, message: str) -> bool:
        return (
            any(term in message for term in {"roadmap", "implementation", "plan", "steps"})
            and any(term in message for term in {"analyze", "analysis", "docs", "document", "findings", "research", "architecture"})
        )

    def _should_plan_then_summarize(self, message: str) -> bool:
        return (
            any(term in message for term in {"brief", "concise", "summary", "summarize"})
            and any(term in message for term in {"plan", "roadmap", "steps"})
        )

    def _is_support_issue(self, message: str) -> bool:
        return any(term in message for term in {"issue", "bug", "error", "problem", "login", "support", "customer"})

    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        self._log_run(ctx)

        message = ctx["request"].message
        retrieval_context: str = ctx.get("retrieval_context", "")
        retrieval_results: list = ctx.get("retrieval_results", [])
        memory: dict = ctx.get("memory", {})
        llm_used = False

        # Enrich plan context with a knowledge-base search when retrieval is empty
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

    # ── LLM path ──────────────────────────────────────────────────────────────

    async def _llm_answer(self, message: str, retrieval_context: str, memory: dict) -> str:
        from app.services.llm.router import call_llm
        return await call_llm(
            agent_name="planner",
            message=message,
            retrieval_context=retrieval_context,
            memory=memory or None,
        )

    # ── Deterministic fallback ─────────────────────────────────────────────────

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

    # ── Scoring ───────────────────────────────────────────────────────────────

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
