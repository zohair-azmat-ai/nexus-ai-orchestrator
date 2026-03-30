from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import get_correlation_id
from app.core.logger import get_logger
from app.db import crud
from app.db.postgres import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.common import ErrorResponse
from app.services.events import logger as event_logger
from app.services.events.types import EVENT_CHAT_RECEIVED, EVENT_CHAT_COMPLETED, EVENT_CHAT_FAILED
from app.services.memory.rules import memory_rules
from app.services.memory.summarizer import conversation_summarizer
from app.services.orchestrator.engine import run_pipeline

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={500: {"model": ErrorResponse}},
    tags=["Chat"],
)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    """
    Submit a chat message for orchestrated processing.

    Flow:
    1. Resolve or create a Conversation record
    2. Persist the user message
    3. Run the orchestrator pipeline
    4. Persist the assistant response
    5. Log a structured event record
    6. Return response with conversation_id and message count
    """
    correlation_id = get_correlation_id()
    logger.info(
        "chat.request",
        extra={
            "correlation_id": correlation_id,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "message_len": len(request.message),
            "conversation_id": request.conversation_id,
        },
    )

    event_logger.emit(EVENT_CHAT_RECEIVED, user_id=request.user_id, session_id=request.session_id)

    # ── Resolve conversation ──────────────────────────────────────────────────
    conversation = await crud.get_or_create_conversation(db, request.user_id, request.conversation_id)

    # ── Persist user message ──────────────────────────────────────────────────
    await crud.create_message(
        db,
        conversation_id=conversation.id,
        role="user",
        content=request.message,
        metadata=request.metadata,
    )

    # ── Orchestrator ──────────────────────────────────────────────────────────
    try:
        pipeline_response = await run_pipeline(
            request, db=db, conversation_id=conversation.id
        )
    except Exception as exc:
        await db.rollback()
        logger.error("chat.error", extra={"error": str(exc), "correlation_id": correlation_id})
        event_logger.emit(EVENT_CHAT_FAILED, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    # ── Persist assistant response ────────────────────────────────────────────
    await crud.create_message(
        db,
        conversation_id=conversation.id,
        role="assistant",
        content=pipeline_response.answer,
        metadata={"agent": pipeline_response.selected_agent},
    )

    # ── Persist event log ─────────────────────────────────────────────────────
    await crud.create_event(
        db,
        correlation_id=correlation_id,
        event_type=EVENT_CHAT_COMPLETED,
        payload={
            "user_id": request.user_id,
            "session_id": request.session_id,
            "conversation_id": conversation.id,
            "agent": pipeline_response.selected_agent,
            "memory_used": pipeline_response.memory_used,
            "retrieval_used": pipeline_response.retrieval_used,
        },
    )

    await db.commit()

    messages_count = await crud.count_messages(db, conversation.id)

    # ── Trigger summary update if threshold reached ───────────────────────────
    if memory_rules.should_summarize(messages_count):
        try:
            recent = await crud.list_recent_messages(
                db, conversation.id, limit=messages_count
            )
            history = [{"role": m.role, "content": m.content} for m in recent]
            summary_text = await conversation_summarizer.summarize(history)
            await crud.upsert_conversation_summary(
                db,
                conversation_id=conversation.id,
                user_id=request.user_id,
                summary_text=summary_text,
                source_message_count=messages_count,
            )
            await db.commit()
            logger.info(
                "chat.summary.updated",
                extra={"conversation_id": conversation.id, "message_count": messages_count},
            )
        except Exception as exc:
            logger.warning(
                "chat.summary.failed",
                extra={"error": str(exc), "conversation_id": conversation.id},
            )

    event_logger.emit(
        EVENT_CHAT_COMPLETED,
        agent=pipeline_response.selected_agent,
        memory_used=pipeline_response.memory_used,
        retrieval_used=pipeline_response.retrieval_used,
        conversation_id=conversation.id,
    )

    return ChatResponse(
        correlation_id=pipeline_response.correlation_id,
        answer=pipeline_response.answer,
        selected_agent=pipeline_response.selected_agent,
        memory_used=pipeline_response.memory_used,
        retrieval_used=pipeline_response.retrieval_used,
        retrieval_result_count=pipeline_response.retrieval_result_count,
        confidence=pipeline_response.confidence,
        conversation_id=conversation.id,
        messages_count=messages_count,
        event_summary=pipeline_response.event_summary,
    )
