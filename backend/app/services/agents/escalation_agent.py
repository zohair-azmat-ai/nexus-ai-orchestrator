"""
Escalation Agent — handles requests requiring immediate human review.

Triggers on: urgent/angry/legal/security/refund/escalate signals.

Behavior:
- Always sets escalation_required = True
- Provides a calm, professional, action-oriented response
- Records the reason for escalation in notes
- High confidence: the selection itself is the correct decision
"""

from typing import Any

from app.services.agents.base import BaseAgent, AgentResult

OrchestratorContext = dict[str, Any]

# Keywords that surface the escalation reason in the response
_REASON_KEYWORDS: dict[str, str] = {
    "legal": "legal concern",
    "sue": "legal concern",
    "lawyer": "legal concern",
    "security": "security issue",
    "breach": "security issue",
    "refund": "billing/refund request",
    "charge": "billing/refund request",
    "fraud": "fraud report",
    "angry": "customer dissatisfaction",
    "frustrated": "customer dissatisfaction",
    "unacceptable": "customer dissatisfaction",
    "urgent": "urgent request",
    "critical": "critical issue",
    "escalate": "explicit escalation request",
    "human": "request for human agent",
    "manager": "request for manager",
    "complaint": "formal complaint",
}


def _detect_reason(message: str) -> str:
    lower = message.lower()
    for keyword, reason in _REASON_KEYWORDS.items():
        if keyword in lower:
            return reason
    return "high-priority request"


class EscalationAgent(BaseAgent):
    name = "escalation"

    async def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        self._log_run(ctx)

        message = ctx["request"].message
        user_id = ctx["request"].user_id
        reason = _detect_reason(message)
        memory: dict = ctx.get("memory", {})
        summary_text: str | None = memory.get("summary_text")

        context_note = ""
        if summary_text:
            context_note = (
                f"\n\nFor context, here is a summary of recent interactions: {summary_text}"
            )

        answer = (
            f"Your request has been escalated for immediate human review.\n\n"
            f"**Reason:** {reason.capitalize()}\n"
            f"**Reference:** User {user_id}{context_note}\n\n"
            "A team member will be with you shortly. "
            "If this is a security or safety emergency, please contact us directly."
        )

        # Set escalated flag early so escalation_stage can read it from agent_result
        ctx["escalated"] = True

        result = self._build_result(
            answer=answer,
            confidence=1.0,
            ctx=ctx,
            escalation_required=True,
            reasoning_summary=f"escalated due to: {reason}",
            notes={"detected_reason": reason},
        )
        ctx["answer"] = answer
        ctx["agent_result"] = result
        return ctx


escalation_agent = EscalationAgent()
