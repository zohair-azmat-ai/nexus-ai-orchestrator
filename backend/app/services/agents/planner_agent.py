"""
Planner Agent — decomposes goals and requests into structured, actionable step-by-step plans.

Behavior:
- Extracts the goal from the user message
- Builds a phased execution plan
- Incorporates retrieval context as reference material when available
- Includes context-aware steps when memory history is present
"""

from typing import Any

from app.services.agents.base import BaseAgent, AgentResult

OrchestratorContext = dict[str, Any]

# Generic plan phases applied when no specific domain is detected
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
        summary_text: str | None = memory.get("summary_text")

        # Build numbered steps
        steps = "\n".join(
            f"**Step {i+1}: {title}**\n   {detail}"
            for i, (title, detail) in enumerate(_DEFAULT_PHASES)
        )

        context_note = ""
        if retrieval_context:
            context_note = (
                "\n\n**Reference material from knowledge base:**\n"
                f"{retrieval_context}\n"
                "Use this as background when executing the plan above."
            )
            confidence = 0.85
            reasoning = "plan enriched with retrieval context"
        elif summary_text:
            context_note = f"\n\n**Prior context:** {summary_text}"
            confidence = 0.75
            reasoning = "plan informed by memory summary"
        else:
            confidence = 0.7
            reasoning = "generic phased plan; no external context"

        answer = (
            f"**Plan for:** \"{message}\"\n\n"
            f"{steps}"
            f"{context_note}\n\n"
            "_Tip: Share more details about your goal to receive a more tailored plan._"
        )

        result = self._build_result(
            answer=answer,
            confidence=confidence,
            ctx=ctx,
            reasoning_summary=reasoning,
        )
        ctx["answer"] = answer
        ctx["agent_result"] = result
        return ctx


planner_agent = PlannerAgent()
