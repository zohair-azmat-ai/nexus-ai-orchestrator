"""
TriggerEscalation tool records a structured escalation signal and can persist
an escalation case when DB context is available.
"""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tools.base_tool import BaseTool


class TriggerEscalationTool(BaseTool):
    name = "trigger_escalation"
    description = (
        "Records an escalation signal with reason, user, and timestamp. "
        "Returns a structured payload that downstream systems can act on."
    )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "user_id": "str - ID of the user triggering the escalation",
            "reason": "str - detected reason for escalation",
            "conversation_id": "str (optional) - conversation being escalated",
            "trace_id": "str (optional) - trace for audit correlation",
            "severity": "str (optional) - escalation severity override",
            "latest_agent": "str (optional) - latest agent involved",
            "latest_summary": "str (optional) - compact case summary",
            "db": "AsyncSession (optional) - persist escalation case when available",
        }

    async def execute(self, **kwargs) -> dict[str, Any]:
        user_id: str = kwargs["user_id"]
        reason: str = kwargs.get("reason", "unspecified")
        conversation_id: str = kwargs.get("conversation_id", "")
        trace_id: str | None = kwargs.get("trace_id")
        severity: str | None = kwargs.get("severity")
        latest_agent: str | None = kwargs.get("latest_agent")
        latest_summary: str | None = kwargs.get("latest_summary")
        db: AsyncSession | None = kwargs.get("db")

        case_id: str | None = None
        case_status = "pending_human_review"
        if db is not None and conversation_id:
            from app.services.escalations.manager import escalation_workflow

            case = await escalation_workflow.ensure_case(
                db,
                conversation_id=conversation_id,
                trace_id=trace_id,
                user_id=user_id,
                escalation_reason=reason,
                severity=severity,
                latest_agent=latest_agent,
                latest_summary=latest_summary,
                note_author=latest_agent or "system",
                note_type="agent" if latest_agent else "system",
            )
            case_id = case.id
            case_status = case.status

        return {
            "escalated": True,
            "user_id": user_id,
            "reason": reason,
            "conversation_id": conversation_id,
            "trace_id": trace_id,
            "case_id": case_id,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
            "status": case_status,
        }


trigger_escalation_tool = TriggerEscalationTool()
