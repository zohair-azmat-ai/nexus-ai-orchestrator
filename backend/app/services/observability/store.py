"""
Lightweight in-memory observability store.

Stores normalized events by trace so the API can expose recent traces without
requiring an external tracing backend.
"""

from collections import defaultdict
from copy import deepcopy
from typing import Any

_trace_events: dict[str, list[dict[str, Any]]] = defaultdict(list)


def record_event(event: dict[str, Any]) -> None:
    trace_id = str(event.get("trace_id", "") or "")
    if not trace_id:
        return
    _trace_events[trace_id].append(deepcopy(event))


def get_trace_events(trace_id: str) -> list[dict[str, Any]]:
    return [deepcopy(event) for event in _trace_events.get(trace_id, [])]


def get_trace_summary(trace_id: str) -> dict[str, Any]:
    events = get_trace_events(trace_id)
    stage_timings: dict[str, float] = {}
    agent_used = ""
    tools_used: list[str] = []

    for event in events:
        stage = event.get("stage", "")
        component = str(event.get("component", "") or "")
        latency_ms = event.get("latency_ms")

        if stage in {"intake", "memory", "retrieval", "triage", "response", "escalation", "event_log"} and isinstance(latency_ms, (int, float)):
            stage_timings[stage] = round(float(latency_ms), 2)

        if event.get("event_type") == "agent.executed" and component:
            agent_used = component

        if stage == "tool" and component and component not in tools_used:
            tools_used.append(component)

    return {
        "trace_id": trace_id,
        "events": events,
        "stage_timings": stage_timings,
        "agent_used": agent_used,
        "tools_used": tools_used,
    }


def reset() -> None:
    _trace_events.clear()
