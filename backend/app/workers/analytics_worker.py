"""
Analytics Worker — aggregates event logs into platform metrics.

Phase 1: stub placeholder.
Phase 4: scheduled job that reads event_log table and writes to metrics store.
"""

from app.core.logger import get_logger
from app.services.analytics.aggregator import get_all

logger = get_logger(__name__)


async def run_analytics_aggregation() -> dict:
    """Aggregate platform counters and return current metrics snapshot."""
    metrics = get_all()
    logger.info("analytics_worker.snapshot", extra={"metrics": metrics})
    return metrics
