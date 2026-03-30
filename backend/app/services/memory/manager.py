"""
Memory Manager — reads and writes conversation context for a given user/session.

Phase 1: in-memory dict store (resets on restart).
Phase 2: backed by PostgreSQL conversation table.
"""

from collections import defaultdict
from typing import Any

from app.core.logger import get_logger
from app.schemas.memory import MemoryEntry, MemoryResponse

logger = get_logger(__name__)

# Phase 1 in-process store: { user_id: { session_id: [entries] } }
_store: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))


class MemoryManager:
    async def load(self, user_id: str, session_id: str) -> dict[str, Any]:
        """Load short-term history for a session."""
        history = _store[user_id][session_id]
        logger.debug("memory.load", extra={"user_id": user_id, "session_id": session_id, "turns": len(history)})
        return {"history": history, "summary": None}

    async def save(self, user_id: str, session_id: str, role: str, content: str) -> None:
        """Append a message turn to the session history."""
        _store[user_id][session_id].append({"role": role, "content": content})
        logger.debug("memory.save", extra={"user_id": user_id, "session_id": session_id, "role": role})

    async def get_user_summary(self, user_id: str) -> MemoryResponse:
        """Return a high-level memory summary for a user."""
        sessions = _store.get(user_id, {})
        all_entries: list[MemoryEntry] = []
        for session_id, turns in sessions.items():
            for turn in turns[-5:]:  # last 5 per session
                all_entries.append(MemoryEntry(role=turn["role"], content=turn["content"]))

        return MemoryResponse(
            user_id=user_id,
            session_count=len(sessions),
            short_term=all_entries,
            long_term_summary=None,
        )

    async def clear(self, user_id: str, session_id: str) -> None:
        """Clear session memory."""
        if user_id in _store and session_id in _store[user_id]:
            del _store[user_id][session_id]


memory_manager = MemoryManager()
