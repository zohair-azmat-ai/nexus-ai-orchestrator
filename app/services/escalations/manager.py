"""
Escalation workflow manager for persistent HITL case handling.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.db import crud
from app.services.events import logger as event_logger
from app.services.events.types import (
    EVENT_ESCALATION_CASE_ASSIGNED,
    EVENT_ESCALATION_CASE_CREATED,
    EVENT_ESCALATION_CASE_STATUS_CHANGED,
    EVENT_ESCALATION_NOTE_ADDED,
)
from app.services.notifications import notifier

logger = get_logger(__name__)

VALID_ESCALATION_STATUSES = {"open", "in_review", "approved", "rejected", "resolved"}
VALID_NOTE_TYPES = {"system", "agent", "human"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}
_STATUS_TRANSITIONS = {
    "open": {"in_review", "approved", "rejected", "resolved"},
    "in_review": {"approved", "rejected", "resolved"},
    "approved": {"resolved"},
    "rejected": {"resolved"},
    "resolved": set(),
}


def infer_severity(reason: str) -> str:
    lower = reason.lower()
    if any(term in lower for term in {"security", "breach", "fraud", "legal", "critical"}):
        return "critical"
    if any(term in lower for term in {
        "urgent", "refund", "manager", "complaint",
        # frustration / cancellation / repeat-issue terms always get high severity
        "terrible", "horrible", "awful", "ridiculous", "fed up",
        "cancel", "cancellation",
        "not resolved", "still not", "third time", "again and again",
        "immediately", "asap",
        "angry", "frustrated",
    }):
        return "high"
    if any(term in lower for term in {"human"}):
        return "medium"
    return "low"


class EscalationWorkflowError(ValueError):
    pass


class EscalationWorkflowManager:
    def validate_status_transition(self, current_status: str, new_status: str) -> None:
        if new_status not in VALID_ESCALATION_STATUSES:
            logger.warning("escalation.invalid_status", extra={"status": new_status})
            raise EscalationWorkflowError(f"Invalid escalation status: {new_status}")
        if new_status == current_status:
            return
        if new_status not in _STATUS_TRANSITIONS.get(current_status, set()):
            logger.warning(
                "escalation.invalid_transition",
                extra={"current_status": current_status, "new_status": new_status},
            )
            raise EscalationWorkflowError(
                f"Invalid escalation status transition: {current_status} -> {new_status}"
            )

    async def ensure_case(
        self,
        db: AsyncSession,
        *,
        conversation_id: str,
        trace_id: str | None,
        user_id: str,
        escalation_reason: str,
        latest_agent: str | None,
        latest_summary: str | None,
        severity: str | None = None,
        note_author: str = "system",
        note_type: str = "system",
        note_content: str | None = None,
        actor: str | None = None,
    ):
        existing = await crud.get_escalation_case_by_trace(db, trace_id or "") if trace_id else None
        if existing is not None:
            return existing

        case_severity = severity or infer_severity(escalation_reason)
        if case_severity not in VALID_SEVERITIES:
            raise EscalationWorkflowError(f"Invalid escalation severity: {case_severity}")
        if note_type not in VALID_NOTE_TYPES:
            raise EscalationWorkflowError(f"Invalid escalation note type: {note_type}")

        case = await crud.create_escalation_case(
            db,
            conversation_id=conversation_id,
            trace_id=trace_id,
            user_id=user_id,
            escalation_reason=escalation_reason,
            severity=case_severity,
            latest_agent=latest_agent,
            latest_summary=latest_summary,
        )
        note_text = note_content or self._default_note(latest_agent, escalation_reason, latest_summary)
        await crud.add_escalation_note(
            db,
            case_id=case.id,
            author=note_author,
            note_type=note_type,
            content=note_text,
        )
        if case.severity == "high":
            case = await self.assign_case(
                db,
                case_id=case.id,
                assigned_to="reviewer_default",
                actor="auto_assigner",
                move_to_in_review=True,
            )
        await notifier.send_notification(db, user_id=user_id, case_id=case.id, channel="email")

        event_logger.emit(
            EVENT_ESCALATION_CASE_CREATED,
            stage="escalation",
            component=latest_agent or "system",
            status="success",
            case_id=case.id,
            severity=case.severity,
            escalation_status=case.status,
            actor=actor or note_author,
        )
        event_logger.emit(
            EVENT_ESCALATION_NOTE_ADDED,
            stage="escalation",
            component=latest_agent or "system",
            status="success",
            case_id=case.id,
            severity=case.severity,
            escalation_status=case.status,
            actor=note_author,
            note_type=note_type,
        )
        return case

    async def assign_case(
        self,
        db: AsyncSession,
        *,
        case_id: str,
        assigned_to: str,
        actor: str | None = None,
        move_to_in_review: bool = True,
    ):
        case = await crud.get_escalation_case(db, case_id)
        if case is None:
            return None
        new_status = "in_review" if move_to_in_review and case.status == "open" else None
        if new_status:
            self.validate_status_transition(case.status, new_status)
        updated = await crud.assign_escalation_case(db, case_id, assigned_to, status=new_status)
        event_logger.emit(
            EVENT_ESCALATION_CASE_ASSIGNED,
            stage="escalation",
            component=updated.latest_agent or "system",
            status="success",
            case_id=updated.id,
            severity=updated.severity,
            escalation_status=updated.status,
            actor=actor or assigned_to,
            assigned_to=assigned_to,
        )
        return updated

    async def update_status(
        self,
        db: AsyncSession,
        *,
        case_id: str,
        new_status: str,
        actor: str | None = None,
    ):
        case = await crud.get_escalation_case(db, case_id)
        if case is None:
            return None
        self.validate_status_transition(case.status, new_status)
        updated = await crud.update_escalation_status(db, case_id, new_status)
        event_logger.emit(
            EVENT_ESCALATION_CASE_STATUS_CHANGED,
            stage="escalation",
            component=updated.latest_agent or "system",
            status="success",
            case_id=updated.id,
            severity=updated.severity,
            escalation_status=updated.status,
            actor=actor or "system",
        )
        return updated

    async def add_note(
        self,
        db: AsyncSession,
        *,
        case_id: str,
        author: str,
        note_type: str,
        content: str,
    ):
        case = await crud.get_escalation_case(db, case_id)
        if case is None:
            return None
        if note_type not in VALID_NOTE_TYPES:
            raise EscalationWorkflowError(f"Invalid escalation note type: {note_type}")
        note = await crud.add_escalation_note(
            db,
            case_id=case_id,
            author=author,
            note_type=note_type,
            content=content,
        )
        event_logger.emit(
            EVENT_ESCALATION_NOTE_ADDED,
            stage="escalation",
            component=case.latest_agent or "system",
            status="success",
            case_id=case.id,
            severity=case.severity,
            escalation_status=case.status,
            actor=author,
            note_type=note_type,
        )
        return note

    def _default_note(self, latest_agent: str | None, reason: str, summary: str | None) -> str:
        prefix = f"Escalated by {latest_agent}." if latest_agent else "Escalation created."
        suffix = f" Summary: {summary}" if summary else ""
        return f"{prefix} Reason: {reason}.{suffix}".strip()


escalation_workflow = EscalationWorkflowManager()
