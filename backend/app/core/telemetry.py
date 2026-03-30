"""
Telemetry stub — structured metrics and tracing placeholders.

Phase 1: no external telemetry dependency.
Phase 5: wire in OpenTelemetry / Prometheus exporters here.
"""

from app.core.logger import get_logger

logger = get_logger(__name__)


def record_event(event_name: str, **attributes: object) -> None:
    """
    Record a named telemetry event with optional attributes.
    In Phase 1 this simply logs the event.
    Future: emit to OTEL span or Prometheus counter.
    """
    logger.info("telemetry.event", extra={"event": event_name, **attributes})


def record_latency(operation: str, duration_ms: float) -> None:
    """Record operation latency. Future: histogram metric."""
    logger.info(
        "telemetry.latency",
        extra={"operation": operation, "duration_ms": round(duration_ms, 2)},
    )
