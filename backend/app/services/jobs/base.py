"""
BaseJob — abstract base class for all Nexus AI background jobs.

Each job must define:
  - job_type  : unique string identifier used in registry lookups
  - execute() : async implementation that accepts a payload dict and returns a result dict

The execute() signature is intentionally simple so the job system can be replaced
with Celery/Dramatiq/RQ without changing individual job implementations.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseJob(ABC):
    job_type: str = "base_job"

    @abstractmethod
    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Run job logic.

        Args:
            payload: Arbitrary dict supplied at submission time.

        Returns:
            Result dict stored in BackgroundJob.result_json.

        Raises on unrecoverable errors — the manager catches these and marks
        the job as failed.
        """

    def __repr__(self) -> str:
        return f"<Job type={self.job_type!r}>"
