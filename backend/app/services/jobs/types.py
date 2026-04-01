"""
Job types and status constants.

Using string constants so they serialize cleanly into JSON logs and DB records.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ─── Status constants ─────────────────────────────────────────────────────────

JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"

# ─── Job type constants ───────────────────────────────────────────────────────

JOB_TYPE_MEMORY_SUMMARY = "memory_summary"
JOB_TYPE_DOCUMENT_INGESTION = "document_ingestion"
JOB_TYPE_ANALYTICS_AGGREGATION = "analytics_aggregation"


# ─── In-memory job record ─────────────────────────────────────────────────────

@dataclass
class JobRecord:
    """Lightweight in-memory representation of a job returned from submit()."""
    job_id: str
    job_type: str
    status: str
    payload: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
