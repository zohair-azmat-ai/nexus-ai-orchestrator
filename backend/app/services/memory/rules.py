"""
Memory Rules — defines when and how memory is read, written, and pruned.

Reads thresholds from application settings so they can be tuned via env vars.
"""

from app.core.config import settings


class MemoryRules:
    @property
    def summarize_after_turns(self) -> int:
        return settings.memory_summary_trigger_count

    @property
    def recent_message_limit(self) -> int:
        return settings.memory_recent_message_limit

    def should_summarize(self, message_count: int) -> bool:
        """Return True when the conversation has hit the summarization threshold."""
        return message_count >= self.summarize_after_turns


memory_rules = MemoryRules()
