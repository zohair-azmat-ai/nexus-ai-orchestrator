"""
Orchestrator policy definitions.

Policies govern routing rules, escalation thresholds, and agent selection
constraints. Values default to the settings singleton so they stay in sync
with environment configuration without requiring a restart.
"""

from dataclasses import dataclass, field


@dataclass
class RoutingPolicy:
    """Controls which agents can be selected and under what conditions."""
    enabled_agents: list[str] = field(default_factory=lambda: [
        "support",
        "research",
        "summarizer",
        "planner",
        "escalation",
    ])
    default_agent: str = "support"
    max_retries: int = 2


@dataclass
class EscalationPolicy:
    """Defines when to escalate a request to human review."""
    escalation_keywords: list[str] = field(default_factory=lambda: [
        "escalate", "urgent", "critical", "human", "manager",
    ])
    confidence_threshold: float = 0.3


@dataclass
class MemoryPolicy:
    """Controls memory read/write behaviour."""
    max_history_turns: int = 20
    enable_long_term_memory: bool = False


def _make_retrieval_policy():
    from app.core.config import settings
    return RetrievalPolicy(
        top_k=settings.rag_top_k,
        min_score=settings.rag_min_score,
        collection_name=settings.qdrant_collection_name,
    )


@dataclass
class RetrievalPolicy:
    """Controls vector search behaviour."""
    top_k: int = 5
    min_score: float = 0.4
    collection_name: str = "nexus_documents"


# Singletons — RetrievalPolicy is lazy so it picks up settings values
routing_policy = RoutingPolicy()
escalation_policy = EscalationPolicy()
memory_policy = MemoryPolicy()

def get_retrieval_policy() -> RetrievalPolicy:
    """Return a RetrievalPolicy populated from current settings."""
    from app.core.config import settings
    return RetrievalPolicy(
        top_k=settings.rag_top_k,
        min_score=settings.rag_min_score,
        collection_name=settings.qdrant_collection_name,
    )


# Module-level instance for backward compat with existing imports
retrieval_policy = RetrievalPolicy()
