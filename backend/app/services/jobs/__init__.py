"""
Jobs package — registers all core job handlers into the global job_registry on import.
"""

from app.services.jobs.registry import job_registry
from app.services.jobs.memory_summary_job import memory_summary_job
from app.services.jobs.document_ingestion_job import document_ingestion_job
from app.services.jobs.analytics_aggregation_job import analytics_aggregation_job

job_registry.register(memory_summary_job)
job_registry.register(document_ingestion_job)
job_registry.register(analytics_aggregation_job)

__all__ = [
    "job_registry",
    "memory_summary_job",
    "document_ingestion_job",
    "analytics_aggregation_job",
]
