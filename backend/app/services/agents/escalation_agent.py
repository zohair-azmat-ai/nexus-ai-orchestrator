"""
Escalation Agent — handles requests requiring immediate human review.

LLM path: empathetic, professional escalation response via OpenAI.
Fallback: template-based escalation message with reason detection.

Always sets escalation_required = True and confidence = 1.0.
"""

from typing import Any

from app.core.config import settings
from app.core.logger import get_logger
from app.services.agents.base import BaseAgent, AgentResult

OrchestratorContext = dict[str, Any]
logger = get_logger(__name__)

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
        retrieval_context: str = ctx.get("retrieval_context", "")
        memory: dict = ctx.get("memory", {})
        reason = _detect_reason(message)
        llm_used = False

        if settings.openai_api_key:
            try:
                answer = await self._llm_answer(message, retrieval_context, memory, reason)
                llm_used = True
            except Exception as exc:
                logger.warning("escalation_agent.llm_failed", extra={"error": str(exc)})
                answer = self._deterministic_answer(message, user_id, memory, reason)
        else:
            answer = self._deterministic_answer(message, user_id, memory, reason)

        # Always escalated, always max confidence
        ctx["escalated"] = True

        result = self._build_result(
            answer=answer,
            confidence=1.0,
            ctx=ctx,
            escalation_required=True,
            reasoning_summary=f"{'llm' if llm_used else 'deterministic fallback'}; escalated due to: {reason}",
            notes={"detected_reason": reason},
        )
        ctx["answer"] = answer
        ctx["agent_result"] = result
        return ctx

    # ── LLM path ──────────────────────────────────────────────────────────────

    async def _llm_answer(
        self, message: str, retrieval_context: str, memory: dict, reason: str
    ) -> str:
        from app.services.llm.router import call_llm
        return await call_llm(
            agent_name="escalation",
            message=message,
            retrieval_context=retrieval_context,
            memory=memory or None,
            detected_reason=reason,
        )

    # ── Deterministic fallback ─────────────────────────────────────────────────

    def _deterministic_answer(
        self, message: str, user_id: str, memory: dict, reason: str
    ) -> str:
        summary_text: str | None = memory.get("summary_text")
        context_note = (
            f"\n\nFor context, here is a summary of recent interactions: {summary_text}"
            if summary_text else ""
        )
        return (
            f"Your request has been escalated for immediate human review.\n\n"
            f"**Reason:** {reason.capitalize()}\n"
            f"**Reference:** User {user_id}{context_note}\n\n"
            "A team member will be with you shortly. "
            "If this is a security or safety emergency, please contact us directly."
        )


escalation_agent = EscalationAgent()
