"""
Planner Agent — decomposes goals into structured, actionable step-by-step plans.

LLM path: generates an intelligent, goal-specific plan using OpenAI.
Fallback: generic 6-phase plan template with context-aware enrichment.
"""

from typing import Any

from app.core.config import settings
from app.core.logger import get_logger
from app.services.agents.base import BaseAgent, AgentResult

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

    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        self._log_run(ctx)

        message = ctx["request"].message
        retrieval_context: str = ctx.get("retrieval_context", "")
        memory: dict = ctx.get("memory", {})
        llm_used = False

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
