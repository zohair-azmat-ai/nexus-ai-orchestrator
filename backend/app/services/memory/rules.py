"""
Memory Rules — defines when and how memory is read, written, and pruned.

Phase 1: constants and simple helpers.
Phase 2: integrate with MemoryManager and session DB.
"""

from dataclasses import dataclass


@dataclass
class MemoryRules:
    # Maximum turns to include in context window
    max_short_term_turns: int = 20

    # Trigger summarization after this many turns
    summarize_after_turns: int = 15

    # Whether to persist summaries to long-term store
    persist_summaries: bool = False  # True in Phase 2

    # Minimum score to consider a memory relevant (future semantic memory)
    relevance_threshold: float = 0.5

    def should_summarize(self, turn_count: int) -> bool:
        return turn_count >= self.summarize_after_turns

    def trim_history(self, history: list[dict]) -> list[dict]:
        """Return the most recent N turns respecting the max limit."""
        return history[-self.max_short_term_turns:]


memory_rules = MemoryRules()
