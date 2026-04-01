"""
Deterministic memory freshness and recent-message compaction helpers.
"""

from dataclasses import dataclass
from typing import Any


_HIGH_SIGNAL_TERMS = {
    "urgent", "broken", "error", "failed", "issue", "problem", "blocked",
    "deadline", "roadmap", "plan", "next steps", "security", "legal",
}
_ASSISTANT_BOILERPLATE = {
    "i'm here to help",
    "please share more details",
    "contact support",
}


@dataclass
class MemoryFreshnessAssessment:
    freshness: str
    selected_recent_messages: list[dict[str, Any]]
    messages_since_summary: int
    high_signal_recent_count: int
    refresh_recommended: bool
    compaction_applied: bool

    def to_metadata(self) -> dict[str, Any]:
        return {
            "memory_freshness": self.freshness,
            "messages_since_summary": self.messages_since_summary,
            "high_signal_recent_count": self.high_signal_recent_count,
            "summary_refresh_recommended": self.refresh_recommended,
            "context_compaction_applied": self.compaction_applied,
        }


def _is_high_signal(message: dict[str, Any]) -> bool:
    content = " ".join(str(message.get("content", "")).split()).strip().lower()
    if len(content) >= 100:
        return True
    return any(term in content for term in _HIGH_SIGNAL_TERMS)


def _is_low_value_assistant_message(message: dict[str, Any]) -> bool:
    if message.get("role") != "assistant":
        return False
    content = " ".join(str(message.get("content", "")).split()).strip().lower()
    return any(fragment in content for fragment in _ASSISTANT_BOILERPLATE)


def select_recent_messages(messages: list[dict[str, Any]], limit: int) -> tuple[list[dict[str, Any]], bool]:
    if not messages:
        return [], False

    chosen: list[tuple[int, int, dict[str, Any]]] = []
    compaction_applied = len(messages) > limit

    for index, message in enumerate(messages):
        if _is_low_value_assistant_message(message):
            compaction_applied = True
            continue
        score = 2 if _is_high_signal(message) else 1
        if message.get("role") == "user":
            score += 1
        chosen.append((score * 1000 + index, index, message))

    chosen = sorted(chosen, key=lambda item: item[0], reverse=True)[:limit]
    selected = [message for _, _, message in sorted(chosen, key=lambda item: item[1])]

    if len(selected) != len(messages):
        compaction_applied = True

    return selected, compaction_applied


def assess_memory_freshness(
    *,
    summary_text: str | None,
    summary_version: int,
    source_message_count: int,
    total_message_count: int,
    recent_messages: list[dict[str, Any]],
    selected_recent_messages: list[dict[str, Any]],
) -> MemoryFreshnessAssessment:
    messages_since_summary = max(total_message_count - source_message_count, 0)
    high_signal_recent_count = sum(1 for message in selected_recent_messages if _is_high_signal(message))
    compaction_applied = selected_recent_messages != recent_messages

    if not summary_text:
        freshness = "recent_only" if selected_recent_messages else "empty"
        refresh_recommended = bool(total_message_count >= 6 and selected_recent_messages)
        return MemoryFreshnessAssessment(
            freshness=freshness,
            selected_recent_messages=selected_recent_messages,
            messages_since_summary=messages_since_summary,
            high_signal_recent_count=high_signal_recent_count,
            refresh_recommended=refresh_recommended,
            compaction_applied=compaction_applied,
        )

    if messages_since_summary >= 6 or high_signal_recent_count >= 2:
        freshness = "stale"
    elif messages_since_summary >= 3 or summary_version <= 1 and high_signal_recent_count >= 1:
        freshness = "aging"
    else:
        freshness = "fresh"

    refresh_recommended = freshness in {"aging", "stale"}
    return MemoryFreshnessAssessment(
        freshness=freshness,
        selected_recent_messages=selected_recent_messages,
        messages_since_summary=messages_since_summary,
        high_signal_recent_count=high_signal_recent_count,
        refresh_recommended=refresh_recommended,
        compaction_applied=compaction_applied,
    )
