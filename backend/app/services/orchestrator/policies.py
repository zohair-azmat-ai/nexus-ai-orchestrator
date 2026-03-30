"""
Orchestrator policy definitions.

Policies govern routing rules, escalation thresholds, and agent selection
constraints. In Phase 1, these are simple constants. In Phase 3+, they can
be loaded from a database or config service for hot-reloading.
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
    confidence_threshold: float = 0.3  # below this, escalate


@dataclass
class MemoryPolicy:
    """Controls memory read/write behaviour."""
    max_history_turns: int = 20
    enable_long_term_memory: bool = False  # enabled in Phase 2


@dataclass
class RetrievalPolicy:
    """Controls vector search behaviour."""
    top_k: int = 5
    min_score: float = 0.6
    collection_name: str = "nexus_documents"


# Singletons used by the orchestrator
routing_policy = RoutingPolicy()
escalation_policy = EscalationPolicy()
memory_policy = MemoryPolicy()
retrieval_policy = RetrievalPolicy()
