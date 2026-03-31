"""
Job Registry — global registry for all registered Nexus AI job handlers.

Usage:
    from app.services.jobs.registry import job_registry

    job_registry.register(my_job)
    handler = job_registry.get("my_job_type")
    all_types = job_registry.list_job_types()
"""

from app.core.logger import get_logger
from app.services.jobs.base import BaseJob

logger = get_logger(__name__)


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, BaseJob] = {}

    def register(self, job: BaseJob) -> None:
        """Register a job handler. Overwrites any existing handler with the same type."""
        if job.job_type in self._jobs:
            logger.warning("job_registry.overwrite", extra={"job_type": job.job_type})
        self._jobs[job.job_type] = job
        logger.debug("job_registry.registered", extra={"job_type": job.job_type})

    def get(self, job_type: str) -> BaseJob | None:
        """Return the handler for the given job_type, or None if not registered."""
        return self._jobs.get(job_type)

    def list_job_types(self) -> list[str]:
        """Return all registered job type names."""
        return list(self._jobs.keys())

    def __len__(self) -> int:
        return len(self._jobs)

    def __contains__(self, job_type: str) -> bool:
        return job_type in self._jobs


# Module-level singleton
job_registry = JobRegistry()
