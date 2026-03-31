"""
CRUD helpers — all database read/write operations for conversations, messages, and events.

These functions accept an AsyncSession and are fully composable. The session is always
managed by the caller (route handler or service), never here.
"""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation, Message
from app.db.models.event import EventLog
from app.db.models.summary import ConversationSummary
from app.db.models.background_job import BackgroundJob
from app.db.models.escalation import EscalationCase, EscalationNote
from app.db.models.user import User
from app.core.logger import get_logger

logger = get_logger(__name__)


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    full_name: str,
    password_hash: str,
    role: str,
    is_active: bool = True,
) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email.strip().lower(),
        full_name=full_name,
        password_hash=password_hash,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    await db.flush()
    logger.debug("crud.user.created", extra={"user_id": user.id, "email": user.email, "role": user.role})
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.strip().lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_or_update_user(
    db: AsyncSession,
    *,
    email: str,
    full_name: str,
    password_hash: str,
    role: str,
    is_active: bool = True,
) -> User:
    user = await get_user_by_email(db, email)
    if user is None:
        return await create_user(
            db,
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )

    user.full_name = full_name
    user.password_hash = password_hash
    user.role = role
    user.is_active = is_active
    user.updated_at = __import__("datetime").datetime.utcnow()
    await db.flush()
    logger.debug("crud.user.updated", extra={"user_id": user.id, "email": user.email, "role": user.role})
    return user


# ─── Conversations ────────────────────────────────────────────────────────────

async def create_conversation(db: AsyncSession, user_id: str) -> Conversation:
    """Create and persist a new conversation for a user."""
    conversation = Conversation(id=str(uuid.uuid4()), user_id=user_id)
    db.add(conversation)
    await db.flush()  # populate id without committing
    logger.debug("crud.conversation.created", extra={"conversation_id": conversation.id, "user_id": user_id})
    return conversation


async def get_conversation(db: AsyncSession, conversation_id: str) -> Conversation | None:
    """Fetch a conversation by ID. Returns None if not found."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    return result.scalar_one_or_none()


async def get_or_create_conversation(
    db: AsyncSession, user_id: str, conversation_id: str | None
) -> Conversation:
    """
    Return an existing conversation if conversation_id is provided and found,
    otherwise create a new one.
    """
    if conversation_id:
        existing = await get_conversation(db, conversation_id)
        if existing:
            return existing
        logger.warning(
            "crud.conversation.not_found",
            extra={"conversation_id": conversation_id, "user_id": user_id},
        )
    return await create_conversation(db, user_id)


# ─── Messages ─────────────────────────────────────────────────────────────────

async def create_message(
    db: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> Message:
    """Append a message to a conversation."""
    message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=role,
        content=content,
        meta=metadata or {},
    )
    db.add(message)
    await db.flush()
    logger.debug(
        "crud.message.created",
        extra={"message_id": message.id, "conversation_id": conversation_id, "role": role},
    )
    return message


async def list_messages(db: AsyncSession, conversation_id: str) -> list[Message]:
    """Return all messages for a conversation, ordered by creation time."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def count_messages(db: AsyncSession, conversation_id: str) -> int:
    """Return the message count for a conversation."""
    result = await db.execute(
        select(func.count()).where(Message.conversation_id == conversation_id)
    )
    return result.scalar_one()


# ─── Events ───────────────────────────────────────────────────────────────────

# ─── Summaries ────────────────────────────────────────────────────────────────

async def get_latest_conversation_summary(
    db: AsyncSession, conversation_id: str
) -> ConversationSummary | None:
    """Fetch the summary row for a conversation, if it exists."""
    result = await db.execute(
        select(ConversationSummary).where(ConversationSummary.conversation_id == conversation_id)
    )
    return result.scalar_one_or_none()


async def upsert_conversation_summary(
    db: AsyncSession,
    conversation_id: str,
    user_id: str,
    summary_text: str,
    source_message_count: int,
) -> ConversationSummary:
    """Insert or update the summary for a conversation."""
    existing = await get_latest_conversation_summary(db, conversation_id)
    if existing:
        existing.summary_text = summary_text
        existing.source_message_count = source_message_count
        existing.summary_version = existing.summary_version + 1
        existing.updated_at = __import__("datetime").datetime.utcnow()
        await db.flush()
        logger.debug("crud.summary.updated", extra={"conversation_id": conversation_id})
        return existing
    summary = ConversationSummary(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        user_id=user_id,
        summary_text=summary_text,
        source_message_count=source_message_count,
        summary_version=1,
    )
    db.add(summary)
    await db.flush()
    logger.debug("crud.summary.created", extra={"conversation_id": conversation_id})
    return summary


async def list_recent_messages(
    db: AsyncSession, conversation_id: str, limit: int
) -> list[Message]:
    """Return the most recent N messages for a conversation, oldest-first."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


# ─── Events ───────────────────────────────────────────────────────────────────

# ─── Background Jobs ──────────────────────────────────────────────────────────

async def create_job(
    db: AsyncSession,
    job_type: str,
    payload: dict[str, Any],
    trace_id: str | None = None,
) -> BackgroundJob:
    """Persist a new background job record in 'queued' status."""
    job = BackgroundJob(
        id=str(uuid.uuid4()),
        trace_id=trace_id,
        job_type=job_type,
        status="queued",
        payload_json=payload,
    )
    db.add(job)
    await db.flush()
    logger.debug("crud.job.created", extra={"job_id": job.id, "job_type": job_type})
    return job


async def update_job_status(
    db: AsyncSession,
    job_id: str,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> BackgroundJob | None:
    """Update job status, and optionally set result or error."""
    job = await get_job_by_id(db, job_id)
    if job is None:
        return None
    job.status = status
    job.updated_at = __import__("datetime").datetime.utcnow()
    if result is not None:
        job.result_json = result
    if error is not None:
        job.error_text = error
    await db.flush()
    logger.debug("crud.job.updated", extra={"job_id": job_id, "status": status})
    return job


async def get_job_by_id(db: AsyncSession, job_id: str) -> BackgroundJob | None:
    """Fetch a background job by its ID."""
    result = await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))
    return result.scalar_one_or_none()


async def list_recent_jobs(
    db: AsyncSession,
    limit: int = 50,
    job_type: str | None = None,
) -> list[BackgroundJob]:
    """Return the most recently created jobs, newest first."""
    query = select(BackgroundJob).order_by(BackgroundJob.created_at.desc()).limit(limit)
    if job_type:
        query = query.where(BackgroundJob.job_type == job_type)
    result = await db.execute(query)
    return list(result.scalars().all())


# â”€â”€â”€ Escalation workflow â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def create_escalation_case(
    db: AsyncSession,
    *,
    conversation_id: str,
    trace_id: str | None,
    user_id: str,
    escalation_reason: str,
    severity: str,
    latest_agent: str | None,
    latest_summary: str | None,
) -> EscalationCase:
    case = EscalationCase(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        trace_id=trace_id,
        user_id=user_id,
        escalation_reason=escalation_reason,
        severity=severity,
        status="open",
        latest_agent=latest_agent,
        latest_summary=latest_summary,
    )
    db.add(case)
    await db.flush()
    logger.debug("crud.escalation_case.created", extra={"case_id": case.id, "status": case.status})
    return case


async def get_escalation_case(db: AsyncSession, case_id: str) -> EscalationCase | None:
    result = await db.execute(select(EscalationCase).where(EscalationCase.id == case_id))
    return result.scalar_one_or_none()


async def get_escalation_case_by_trace(db: AsyncSession, trace_id: str) -> EscalationCase | None:
    result = await db.execute(
        select(EscalationCase)
        .where(EscalationCase.trace_id == trace_id)
        .order_by(EscalationCase.created_at.desc())
    )
    return result.scalars().first()


async def list_escalation_cases(
    db: AsyncSession,
    *,
    limit: int = 50,
    status: str | None = None,
    severity: str | None = None,
    assigned_to: str | None = None,
) -> list[EscalationCase]:
    query = select(EscalationCase).order_by(EscalationCase.created_at.desc()).limit(limit)
    if status:
        query = query.where(EscalationCase.status == status)
    if severity:
        query = query.where(EscalationCase.severity == severity)
    if assigned_to:
        query = query.where(EscalationCase.assigned_to == assigned_to)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_escalation_status(
    db: AsyncSession,
    case_id: str,
    status: str,
) -> EscalationCase | None:
    case = await get_escalation_case(db, case_id)
    if case is None:
        return None
    case.status = status
    case.updated_at = __import__("datetime").datetime.utcnow()
    await db.flush()
    logger.debug("crud.escalation_case.status_updated", extra={"case_id": case_id, "status": status})
    return case


async def assign_escalation_case(
    db: AsyncSession,
    case_id: str,
    assigned_to: str,
    *,
    status: str | None = None,
) -> EscalationCase | None:
    case = await get_escalation_case(db, case_id)
    if case is None:
        return None
    case.assigned_to = assigned_to
    if status:
        case.status = status
    case.updated_at = __import__("datetime").datetime.utcnow()
    await db.flush()
    logger.debug("crud.escalation_case.assigned", extra={"case_id": case_id, "assigned_to": assigned_to})
    return case


async def add_escalation_note(
    db: AsyncSession,
    *,
    case_id: str,
    author: str,
    note_type: str,
    content: str,
) -> EscalationNote:
    note = EscalationNote(
        id=str(uuid.uuid4()),
        case_id=case_id,
        author=author,
        note_type=note_type,
        content=content,
    )
    db.add(note)
    await db.flush()
    logger.debug("crud.escalation_note.created", extra={"case_id": case_id, "note_id": note.id})
    return note


async def list_escalation_notes(db: AsyncSession, case_id: str) -> list[EscalationNote]:
    result = await db.execute(
        select(EscalationNote)
        .where(EscalationNote.case_id == case_id)
        .order_by(EscalationNote.created_at.asc())
    )
    return list(result.scalars().all())


async def create_event(
    db: AsyncSession,
    correlation_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> EventLog:
    """Persist a platform event to the event_logs table."""
    event = EventLog(
        id=str(uuid.uuid4()),
        correlation_id=correlation_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(event)
    await db.flush()
    logger.debug(
        "crud.event.created",
        extra={"event_id": event.id, "event_type": event_type, "correlation_id": correlation_id},
    )
    return event
