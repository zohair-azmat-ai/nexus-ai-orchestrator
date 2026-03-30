"""
Analytics Aggregator — computes platform usage metrics.

Phase 1: in-memory counters only.
Phase 4: reads from the event_log table and produces real analytics.
"""

from collections import defaultdict
from typing import Any

_counters: dict[str, int] = defaultdict(int)


def increment(metric: str, value: int = 1) -> None:
    """Increment a named counter metric."""
    _counters[metric] += value


def get_all() -> dict[str, Any]:
    """Return all current metric counters."""
    return dict(_counters)


def get_metric(metric: str) -> int:
    return _counters.get(metric, 0)
