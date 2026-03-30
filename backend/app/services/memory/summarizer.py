"""
Conversation Summarizer — condenses long history into a compact summary.

Phase 1: returns a placeholder string.
Phase 2: calls OpenAI to produce a real summary, persists to DB.
"""

from app.core.logger import get_logger

logger = get_logger(__name__)


class ConversationSummarizer:
    async def summarize(self, history: list[dict]) -> str:
        """
        Summarize a list of message turns.

        Args:
            history: list of {"role": str, "content": str} dicts

        Returns:
            A string summary.
        """
        if not history:
            return ""

        # Phase 2: replace with real LLM summarization call
        logger.info("summarizer.stub", extra={"turns": len(history)})
        return f"[Summary of {len(history)} turns — Phase 2 will implement LLM-based summarization]"


conversation_summarizer = ConversationSummarizer()
