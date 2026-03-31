"""
Deterministic retrieval-quality assessment and context compaction helpers.
"""

from dataclasses import dataclass
from typing import Any


_MIN_TEXT_LEN = 40
_MAX_CONTEXT_RESULTS = 3
_STRONG_TOP_SCORE = 0.82
_STRONG_AVG_SCORE = 0.74
_WEAK_TOP_SCORE = 0.62
_MAX_SCORE_SPREAD = 0.18


@dataclass
class RetrievalAssessment:
    quality: str
    compacted_results: list[dict[str, Any]]
    compacted_context: str
    compaction_applied: bool
    top_score: float
    average_score: float
    score_spread: float
    meaningful_count: int

    def to_metadata(self) -> dict[str, Any]:
        return {
            "retrieval_quality": self.quality,
            "top_score": self.top_score,
            "average_score": self.average_score,
            "score_spread": self.score_spread,
            "meaningful_count": self.meaningful_count,
            "context_compaction_applied": self.compaction_applied,
        }


def _normalize_text(text: str) -> str:
    return " ".join((text or "").split()).strip()


def _is_meaningful_result(result: dict[str, Any]) -> bool:
    text = _normalize_text(str(result.get("text", "")))
    if len(text) < _MIN_TEXT_LEN:
        return False
    token_count = len(text.split())
    if token_count < 6:
        return False
    return any(ch.isalpha() for ch in text)


def compact_results(results: list[dict[str, Any]], max_results: int = _MAX_CONTEXT_RESULTS) -> tuple[list[dict[str, Any]], bool]:
    compacted: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    compaction_applied = False

    ordered = sorted(results, key=lambda item: float(item.get("score", 0.0)), reverse=True)
    for result in ordered:
        if not _is_meaningful_result(result):
            compaction_applied = True
            continue

        text = _normalize_text(str(result.get("text", "")))
        doc_id = str(result.get("document_id") or result.get("source") or "")
        dedupe_key = (doc_id, text.lower())
        if dedupe_key in seen_keys:
            compaction_applied = True
            continue

        compacted.append(
            {
                "chunk_id": result.get("chunk_id", ""),
                "document_id": result.get("document_id", ""),
                "chunk_index": result.get("chunk_index", 0),
                "text": text,
                "score": round(float(result.get("score", 0.0)), 4),
                "source": result.get("source", "") or result.get("document_id", "") or "unknown",
            }
        )
        seen_keys.add(dedupe_key)
        if len(compacted) >= max_results:
            if len(ordered) > len(compacted):
                compaction_applied = True
            break

    if len(compacted) != len(results):
        compaction_applied = True

    return compacted, compaction_applied


def format_compact_context(results: list[dict[str, Any]]) -> str:
    if not results:
        return ""

    parts = []
    for index, result in enumerate(results, start=1):
        source_label = result.get("source") or result.get("document_id") or "unknown"
        parts.append(f"[{index}] (source: {source_label}, score: {result['score']})\n{result['text']}")
    return "\n\n---\n\n".join(parts)


def assess_retrieval_quality(results: list[dict[str, Any]]) -> RetrievalAssessment:
    compacted_results, compaction_applied = compact_results(results)
    if not compacted_results:
        return RetrievalAssessment(
            quality="none",
            compacted_results=[],
            compacted_context="",
            compaction_applied=compaction_applied,
            top_score=0.0,
            average_score=0.0,
            score_spread=0.0,
            meaningful_count=0,
        )

    scores = [float(item.get("score", 0.0)) for item in compacted_results]
    top_score = max(scores)
    average_score = sum(scores) / len(scores)
    score_spread = top_score - min(scores)

    if (
        len(compacted_results) >= 2
        and top_score >= _STRONG_TOP_SCORE
        and average_score >= _STRONG_AVG_SCORE
        and score_spread <= _MAX_SCORE_SPREAD
    ):
        quality = "strong"
    elif top_score >= _WEAK_TOP_SCORE:
        quality = "weak"
    else:
        quality = "none"

    return RetrievalAssessment(
        quality=quality,
        compacted_results=compacted_results,
        compacted_context=format_compact_context(compacted_results),
        compaction_applied=compaction_applied,
        top_score=round(top_score, 4),
        average_score=round(average_score, 4),
        score_spread=round(score_spread, 4),
        meaningful_count=len(compacted_results),
    )
