"""
GetUserContext tool — fetches full memory context for a user/conversation from DB.

Combines the stored summary with the most recent messages into a single
structured context dict, giving agents richer data than the memory stage alone.
"""

from typing import Any

from app.services.tools.base_tool import BaseTool


class GetUserContextTool(BaseTool):
    name = "get_user_context"
    description = (
        "Fetches the stored conversation summary and recent messages for a user. "
        "Returns structured memory context including summary text and message history."
    )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "db": "AsyncSession — active database session",
            "conversation_id": "str — UUID of the conversation",
            "user_id": "str — user identifier",
        }

    async def execute(self, **kwargs) -> dict[str, Any]:
        from app.db import crud
        from app.core.config import settings

        db = kwargs["db"]
        conversation_id: str = kwargs["conversation_id"]
        user_id: str = kwargs["user_id"]
        limit: int = settings.memory_recent_message_limit

        summary = await crud.get_latest_conversation_summary(db, conversation_id)
        messages = await crud.list_recent_messages(db, conversation_id, limit=limit)

        summary_text = summary.summary_text if summary else None
        recent = [{"role": m.role, "content": m.content} for m in messages]
        memory_used = bool(summary_text or recent)

        return {
            "summary_text": summary_text,
            "recent_messages": recent,
            "memory_used": memory_used,
            "memory_source": "db",
            "message_count": len(recent),
            "user_id": user_id,
        }


get_user_context_tool = GetUserContextTool()
