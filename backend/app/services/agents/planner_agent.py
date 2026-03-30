"""
Planner Agent — decomposes complex goals into actionable step-by-step plans.
"""

from typing import Any

from app.services.agents.base import BaseAgent

OrchestratorContext = dict[str, Any]


class PlannerAgent(BaseAgent):
    name = "planner"

    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        self._log_run(ctx)
        message = ctx["request"].message

        # Phase 3: call LLM with chain-of-thought planning prompt
        ctx["answer"] = (
            f"Plan for: '{message}'.\n"
            "Step 1: [Analyze requirements]\n"
            "Step 2: [Identify resources]\n"
            "Step 3: [Execute]\n"
            "(Phase 3 will generate real LLM-powered plans.)"
        )
        return ctx


planner_agent = PlannerAgent()
