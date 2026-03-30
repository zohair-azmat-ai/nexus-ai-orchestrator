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
from app.core.logger import get_logger

logger = get_logger(__name__)


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
