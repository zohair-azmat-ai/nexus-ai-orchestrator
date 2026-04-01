"""
Event Logger — records structured platform events.

Phase 1: writes events to the structured log stream.
Phase 4: persists events to a PostgreSQL event_log table.
"""

from datetime import datetime
from typing import Any

from app.core.ids import generate_id, get_correlation_id, get_trace_id
from app.core.logger import get_logger
from app.services.analytics import aggregator
from app.services.observability import store as trace_store

logger = get_logger("nexus.events")


def emit(event_type: str, **payload: Any) -> None:
    """
    Emit a named event with arbitrary payload fields.

    Every emitted event gets:
    - event_id: unique identifier
    - event_type: the event name
    - correlation_id: from current request context
    - timestamp: UTC ISO string
    """
    stage = payload.pop("stage", "system")
    component = payload.pop("component", "")
    latency_ms = payload.pop("latency_ms", None)
    status = payload.pop("status", "success")
    trace_id = payload.pop("trace_id", None) or get_trace_id()

    event = {
        "event_id": generate_id(),
        "event_type": event_type,
        "trace_id": trace_id,
        "correlation_id": get_correlation_id(),
        "stage": stage,
        "component": component,
        "latency_ms": latency_ms,
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        **payload,
    }

    if event_type == "agent.executed" and component:
        aggregator.record_agent_usage(component)
    if stage == "tool" and component and event_type == "tool.result":
        aggregator.record_tool_usage(component)
    if stage == "job" and component:
        aggregator.record_job(component, status)
    if status == "fail":
        aggregator.record_error(component or stage)

    trace_store.record_event(event)
    logger.info("event", extra=event)
