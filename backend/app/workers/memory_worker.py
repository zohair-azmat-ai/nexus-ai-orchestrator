"""
Memory Worker — runs background summarization and memory compaction.

Phase 1: stub placeholder.
Phase 4: scheduled job that summarizes old sessions and prunes short-term history.
"""

from app.core.logger import get_logger

logger = get_logger(__name__)


async def run_memory_compaction(user_id: str) -> None:
    """
    Compact and summarize old session memory for a user.

    Phase 4: call ConversationSummarizer, persist to long-term store.
    """
    logger.info("memory_worker.stub", extra={"user_id": user_id})
