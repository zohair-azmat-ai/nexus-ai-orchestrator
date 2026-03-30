"""
Event Logger — records structured platform events.

Phase 1: writes events to the structured log stream.
Phase 4: persists events to a PostgreSQL event_log table.
"""

from datetime import datetime
from typing import Any

from app.core.ids import generate_id, get_correlation_id
from app.core.logger import get_logger

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
    event = {
        "event_id": generate_id(),
        "event_type": event_type,
        "correlation_id": get_correlation_id(),
        "timestamp": datetime.utcnow().isoformat(),
        **payload,
    }
    logger.info("event", extra=event)
