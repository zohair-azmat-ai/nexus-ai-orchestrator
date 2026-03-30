"""
Memory Manager — reads conversation context from PostgreSQL.

Loads the latest summary plus the N most-recent messages for a conversation,
providing the orchestrator with structured memory context.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.db import crud
from app.schemas.memory import MemoryEntry, MemoryResponse
from app.services.memory.freshness import assess_memory_freshness, select_recent_messages
from app.services.memory.rules import memory_rules

logger = get_logger(__name__)


class MemoryManager:
    async def load(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Load memory context for a conversation.

        Returns a dict with:
          - summary_text: latest LLM summary (or None)
          - recent_messages: list of recent Message ORM objects
          - memory_used: True when any context was found
          - memory_source: "db"
          - message_count: total recent messages returned
        """
        summary = await crud.get_latest_conversation_summary(db, conversation_id)
        recent = await crud.list_recent_messages(
            db, conversation_id, limit=memory_rules.recent_message_limit
        )
        total_message_count = await crud.count_messages(db, conversation_id)

        summary_text = summary.summary_text if summary else None
        raw_recent_messages = [{"role": m.role, "content": m.content} for m in recent]
        selected_recent_messages, recent_compacted = select_recent_messages(
            raw_recent_messages,
            limit=memory_rules.recent_message_limit,
        )
        freshness = assess_memory_freshness(
            summary_text=summary_text,
            summary_version=summary.summary_version if summary else 0,
            source_message_count=summary.source_message_count if summary else 0,
            total_message_count=total_message_count,
            recent_messages=raw_recent_messages,
            selected_recent_messages=selected_recent_messages,
        )
        memory_used = bool(summary_text or selected_recent_messages)

        logger.debug(
            "memory.load",
            extra={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "has_summary": summary_text is not None,
                "recent_count": len(selected_recent_messages),
                "memory_freshness": freshness.freshness,
            },
        )

        return {
            "summary_text": summary_text,
            "recent_messages": selected_recent_messages,
            "memory_used": memory_used,
            "memory_source": "db",
            "message_count": len(selected_recent_messages),
            "total_message_count": total_message_count,
            "summary_version": summary.summary_version if summary else 0,
            "source_message_count": summary.source_message_count if summary else 0,
            "memory_freshness": freshness.freshness,
            "messages_since_summary": freshness.messages_since_summary,
            "high_signal_recent_count": freshness.high_signal_recent_count,
            "summary_refresh_recommended": freshness.refresh_recommended,
            "context_compaction_applied": recent_compacted or freshness.compaction_applied,
        }

    async def get_user_summary(self, db: AsyncSession, user_id: str) -> MemoryResponse:
        """
        Return a high-level memory overview for the memory API endpoint.

        Fetches all summaries belonging to the user and surfaces recent messages
        from the most recently updated conversation.
        """
        from sqlalchemy import select
        from app.db.models.summary import ConversationSummary
        from app.db.models.conversation import Conversation

        result = await db.execute(
            select(ConversationSummary)
            .where(ConversationSummary.user_id == user_id)
            .order_by(ConversationSummary.updated_at.desc())
        )
        summaries = result.scalars().all()

        conv_result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
        )
        conversations = conv_result.scalars().all()

        long_term = summaries[0].summary_text if summaries else None

        short_term: list[MemoryEntry] = []
        if conversations:
            latest_conv = max(conversations, key=lambda c: c.updated_at)
            recent = await crud.list_recent_messages(
                db, latest_conv.id, limit=memory_rules.recent_message_limit
            )
            short_term = [MemoryEntry(role=m.role, content=m.content) for m in recent]

        return MemoryResponse(
            user_id=user_id,
            session_count=len(conversations),
            short_term=short_term,
            long_term_summary=long_term,
        )


memory_manager = MemoryManager()
