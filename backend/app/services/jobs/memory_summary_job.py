"""
MemorySummaryJob — generates and persists a conversation summary.

Payload keys:
  conversation_id : str  — conversation to summarize
  user_id         : str  — owner of the conversation

Uses ConversationSummarizer (LLM or deterministic fallback) and upserts
the result into the conversation_summaries table.
"""

from typing import Any

from app.db.postgres import _get_session_local
from app.services.memory.summarizer import conversation_summarizer
from app.services.jobs.base import BaseJob
from app.services.jobs.types import JOB_TYPE_MEMORY_SUMMARY
from app.core.logger import get_logger

logger = get_logger(__name__)


class MemorySummaryJob(BaseJob):
    job_type = JOB_TYPE_MEMORY_SUMMARY

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        from app.db import crud

        conversation_id: str = payload["conversation_id"]
        user_id: str = payload["user_id"]

        async with _get_session_local()() as db:
            messages = await crud.list_recent_messages(
                db, conversation_id, limit=payload.get("limit", 50)
            )
            if not messages:
                logger.info(
                    "memory_summary_job.no_messages",
                    extra={"conversation_id": conversation_id},
                )
                return {"summary_text": "", "message_count": 0, "conversation_id": conversation_id}

            history = [{"role": m.role, "content": m.content} for m in messages]
            summary_text = await conversation_summarizer.summarize(history)

            await crud.upsert_conversation_summary(
                db,
                conversation_id=conversation_id,
                user_id=user_id,
                summary_text=summary_text,
                source_message_count=len(messages),
            )
            await db.commit()

        logger.info(
            "memory_summary_job.done",
            extra={"conversation_id": conversation_id, "message_count": len(messages)},
        )
        return {
            "summary_text": summary_text,
            "message_count": len(messages),
            "conversation_id": conversation_id,
        }


memory_summary_job = MemorySummaryJob()
