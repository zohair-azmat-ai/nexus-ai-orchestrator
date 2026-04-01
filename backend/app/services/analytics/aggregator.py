"""
Analytics Aggregator — computes platform usage metrics.

Phase 1: in-memory counters only.
Phase 4: reads from the event_log table and produces real analytics.
"""

from collections import defaultdict
from typing import Any

_counters: dict[str, int] = defaultdict(int)
_agent_usage: dict[str, int] = defaultdict(int)
_tool_usage: dict[str, int] = defaultdict(int)
_job_counts: dict[str, int] = defaultdict(int)
_error_counts: dict[str, int] = defaultdict(int)


def increment(metric: str, value: int = 1) -> None:
    """Increment a named counter metric."""
    _counters[metric] += value


def get_all() -> dict[str, Any]:
    """Return all current metric counters."""
    return dict(_counters)


def get_metric(metric: str) -> int:
    return _counters.get(metric, 0)


def record_request() -> None:
    increment("total_requests")


def record_agent_usage(agent_name: str) -> None:
    _agent_usage[agent_name] += 1
    increment(f"agent.{agent_name}")


def record_tool_usage(tool_name: str) -> None:
    _tool_usage[tool_name] += 1
    increment(f"tool.{tool_name}")


def record_job(job_name: str, status: str) -> None:
    key = f"{job_name}:{status}"
    _job_counts[key] += 1
    increment(f"job.{job_name}.{status}")


def record_error(component: str) -> None:
    name = component or "unknown"
    _error_counts[name] += 1
    increment("errors.total")
    increment(f"errors.{name}")


def get_metrics_snapshot() -> dict[str, Any]:
    return {
        "total_requests": get_metric("total_requests"),
        "agent_usage": dict(_agent_usage),
        "tool_usage": dict(_tool_usage),
        "job_counts": dict(_job_counts),
        "error_counts": dict(_error_counts),
        "counters": get_all(),
    }


def reset() -> None:
    _counters.clear()
    _agent_usage.clear()
    _tool_usage.clear()
    _job_counts.clear()
    _error_counts.clear()
