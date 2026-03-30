"""
Escalation Agent — handles requests that require human review or urgent action.
"""

from typing import Any

from app.services.agents.base import BaseAgent

OrchestratorContext = dict[str, Any]


class EscalationAgent(BaseAgent):
    name = "escalation"

    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        self._log_run(ctx)
        user_id = ctx["request"].user_id

        ctx["escalated"] = True
        ctx["answer"] = (
            f"Your request has been flagged for escalation (user: {user_id}). "
            "A human agent will review this shortly. "
            "(Phase 4 will trigger real escalation workflows.)"
        )
        return ctx


escalation_agent = EscalationAgent()
