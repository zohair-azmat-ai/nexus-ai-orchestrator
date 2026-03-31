"""
AnalyticsAggregationJob — snapshot current in-memory analytics metrics.

Payload: {} (no required keys)

Returns a point-in-time snapshot of all counters from the analytics aggregator.
Phase 4: reads from the EventLog table for real aggregation in the future.
"""

from typing import Any

from app.services.jobs.base import BaseJob
from app.services.jobs.types import JOB_TYPE_ANALYTICS_AGGREGATION
from app.core.logger import get_logger

logger = get_logger(__name__)


class AnalyticsAggregationJob(BaseJob):
    job_type = JOB_TYPE_ANALYTICS_AGGREGATION

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        from app.services.analytics.aggregator import get_all
        from datetime import datetime

        metrics = get_all()
        snapshot = {
            "metrics": metrics,
            "total_counters": len(metrics),
            "snapshot_at": datetime.utcnow().isoformat(),
        }
        logger.info(
            "analytics_aggregation_job.done",
            extra={"total_counters": snapshot["total_counters"]},
        )
        return snapshot


analytics_aggregation_job = AnalyticsAggregationJob()
