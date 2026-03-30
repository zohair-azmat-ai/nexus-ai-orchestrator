from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import get_correlation_id, get_trace_id
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
from app.services.jobs.manager import job_manager
from app.services.jobs.types import JOB_TYPE_MEMORY_SUMMARY

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
    trace_id = get_trace_id() or correlation_id
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

    event_logger.emit(
        EVENT_CHAT_RECEIVED,
        stage="intake",
        component="chat",
        status="success",
        user_id=request.user_id,
        session_id=request.session_id,
    )

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
        event_logger.emit(
            EVENT_CHAT_FAILED,
            stage="response",
            component="chat",
            status="fail",
            error=str(exc),
        )
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
            "trace_id": trace_id,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "conversation_id": conversation.id,
            "agent": pipeline_response.selected_agent,
            "final_agent": pipeline_response.final_agent,
            "memory_used": pipeline_response.memory_used,
            "retrieval_used": pipeline_response.retrieval_used,
            "retrieval_quality": pipeline_response.retrieval_quality,
            "memory_freshness": pipeline_response.memory_freshness,
            "context_sources_used": pipeline_response.context_sources_used,
            "context_compaction_applied": pipeline_response.context_compaction_applied,
            "stage_timings": pipeline_response.stage_timings,
            "execution_mode": pipeline_response.execution_mode,
            "executed_steps_count": pipeline_response.executed_steps_count,
            "skipped_steps_count": pipeline_response.skipped_steps_count,
            "tools_planned": pipeline_response.tools_planned,
            "plan_summary": pipeline_response.plan_summary,
            "execution_plan_summary": pipeline_response.execution_plan_summary,
        },
    )

    await db.commit()

    messages_count = await crud.count_messages(db, conversation.id)

    # ── Trigger summary update if threshold reached ───────────────────────────
    if memory_rules.should_summarize(messages_count):
        from app.core.config import settings as _settings
        if _settings.enable_async_memory_summary:
            # Queue as a background job — returns quickly, summary generated async
            try:
                await job_manager.submit(
                    db,
                    JOB_TYPE_MEMORY_SUMMARY,
                    {"conversation_id": conversation.id, "user_id": request.user_id},
                )
                await db.commit()
                logger.info(
                    "chat.summary.queued",
                    extra={"conversation_id": conversation.id},
                )
            except Exception as exc:
                logger.warning(
                    "chat.summary.queue_failed",
                    extra={"error": str(exc), "conversation_id": conversation.id},
                )
        else:
            # Inline (default) — existing synchronous path
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
        stage="response",
        component="chat",
        status="success",
        agent=pipeline_response.selected_agent,
        final_agent=pipeline_response.final_agent,
        memory_used=pipeline_response.memory_used,
        retrieval_used=pipeline_response.retrieval_used,
        conversation_id=conversation.id,
        stage_timings=pipeline_response.stage_timings,
        execution_mode=pipeline_response.execution_mode,
        executed_steps_count=pipeline_response.executed_steps_count,
        skipped_steps_count=pipeline_response.skipped_steps_count,
        retrieval_quality=pipeline_response.retrieval_quality,
        memory_freshness=pipeline_response.memory_freshness,
        context_sources_used=pipeline_response.context_sources_used,
        context_compaction_applied=pipeline_response.context_compaction_applied,
        tools_planned=pipeline_response.tools_planned,
    )

    return ChatResponse(
        correlation_id=pipeline_response.correlation_id,
        trace_id=pipeline_response.trace_id,
        answer=pipeline_response.answer,
        selected_agent=pipeline_response.selected_agent,
        execution_mode=pipeline_response.execution_mode,
        executed_steps_count=pipeline_response.executed_steps_count,
        skipped_steps_count=pipeline_response.skipped_steps_count,
        final_agent=pipeline_response.final_agent,
        memory_used=pipeline_response.memory_used,
        retrieval_used=pipeline_response.retrieval_used,
        retrieval_result_count=pipeline_response.retrieval_result_count,
        retrieval_quality=pipeline_response.retrieval_quality,
        confidence=pipeline_response.confidence,
        memory_freshness=pipeline_response.memory_freshness,
        context_sources_used=pipeline_response.context_sources_used,
        context_compaction_applied=pipeline_response.context_compaction_applied,
        tools_planned=pipeline_response.tools_planned,
        tools_used=pipeline_response.tools_used,
        stage_timings=pipeline_response.stage_timings,
        plan_summary=pipeline_response.plan_summary,
        execution_plan_summary=pipeline_response.execution_plan_summary,
        conversation_id=conversation.id,
        messages_count=messages_count,
        event_summary=pipeline_response.event_summary,
    )
