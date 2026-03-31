"""
GetConversationHistory tool — fetches recent messages for a conversation from DB.

Returns the N most recent messages in chronological order so agents can
access fresh conversation context beyond what the memory stage loaded.
"""

from typing import Any

from app.services.tools.base_tool import BaseTool


class GetConversationHistoryTool(BaseTool):
    name = "get_conversation_history"
    description = (
        "Retrieves recent messages from a conversation stored in the database. "
        "Returns messages in chronological order with role and content."
    )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "db": "AsyncSession — active database session",
            "conversation_id": "str — UUID of the conversation",
            "limit": "int (optional, default 10) — max number of messages to return",
        }

    async def execute(self, **kwargs) -> dict[str, Any]:
        from app.db import crud

        db = kwargs["db"]
        conversation_id = kwargs["conversation_id"]
        limit: int = kwargs.get("limit", 10)

        messages = await crud.list_recent_messages(db, conversation_id, limit=limit)
        formatted = [{"role": m.role, "content": m.content} for m in messages]

        return {
            "messages": formatted,
            "count": len(formatted),
            "conversation_id": conversation_id,
        }


get_conversation_history_tool = GetConversationHistoryTool()
