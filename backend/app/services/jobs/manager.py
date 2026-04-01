"""
Job Manager — submits, dispatches, and tracks background jobs.

Execution modes (controlled by settings.jobs_inline_mode):
  - Inline (default / tests): job runs synchronously in the same session as the caller.
    Easiest to reason about; no extra sessions or asyncio tasks needed.
  - Async: job record is created in the caller's session (flushed, not committed),
    then an asyncio.create_task() fires the job with its own DB session.

Plug-in path: replace _run_background() with a Celery/Dramatiq/RQ enqueue call
to move to a true distributed queue without touching callers or job handlers.
"""

import asyncio
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.ids import get_trace_id, set_trace_id
from app.core.logger import get_logger
from app.services.jobs.registry import job_registry
from app.services.jobs.types import (
    JOB_STATUS_RUNNING,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JobRecord,
)

logger = get_logger(__name__)


def _job_to_record(job_row: Any) -> JobRecord:
    return JobRecord(
        job_id=job_row.id,
        job_type=job_row.job_type,
        status=job_row.status,
        payload=job_row.payload_json or {},
        result=job_row.result_json,
        error=job_row.error_text,
        created_at=job_row.created_at,
        updated_at=job_row.updated_at,
    )


class JobManager:
    async def submit(
        self,
        db: AsyncSession,
        job_type: str,
        payload: dict[str, Any],
    ) -> JobRecord:
        """
        Create a job record and execute it (inline or background).

        Args:
            db:       Active DB session (used to persist the job row).
            job_type: Registered job type string.
            payload:  Arbitrary dict passed to the job handler.

        Returns:
            JobRecord reflecting the final state (inline) or 'queued' (async).
        """
        import app.services.jobs  # ensure all handlers are registered  # noqa: F401
        from app.db import crud
        from app.services.events.types import EVENT_JOB_CREATED
        from app.services.events import logger as event_logger

        trace_id = get_trace_id() or payload.get("trace_id") or ""
        job_row = await crud.create_job(db, job_type=job_type, payload=payload, trace_id=trace_id or None)
        event_logger.emit(
            EVENT_JOB_CREATED,
            trace_id=trace_id,
            stage="job",
            component=job_type,
            status="queued",
            job_id=job_row.id,
            job_type=job_type,
        )
        logger.info("job.created", extra={"job_id": job_row.id, "job_type": job_type})

        if settings.jobs_inline_mode:
            await self._execute(db, job_row.id, job_type, payload, trace_id=trace_id)
        else:
            asyncio.create_task(
                self._run_background(job_row.id, job_type, payload, trace_id=trace_id)
            )

        # Reload to pick up status changes made by _execute (inline mode)
        refreshed = await crud.get_job_by_id(db, job_row.id)
        return _job_to_record(refreshed if refreshed else job_row)

    # ── Core execution ────────────────────────────────────────────────────────

    async def _execute(
        self,
        db: AsyncSession,
        job_id: str,
        job_type: str,
        payload: dict[str, Any],
        trace_id: str = "",
    ) -> None:
        """Run a job handler within the given session."""
        from app.db import crud
        from app.services.events.types import EVENT_JOB_STARTED, EVENT_JOB_COMPLETED, EVENT_JOB_FAILED
        from app.services.events import logger as event_logger

        if trace_id:
            set_trace_id(trace_id)

        handler = job_registry.get(job_type)
        if handler is None:
            logger.error("job.unknown_type", extra={"job_id": job_id, "job_type": job_type})
            await crud.update_job_status(db, job_id, JOB_STATUS_FAILED, error=f"Unknown job type: {job_type!r}")
            event_logger.emit(
                EVENT_JOB_FAILED,
                trace_id=trace_id,
                stage="job",
                component=job_type,
                status="fail",
                job_id=job_id,
                job_type=job_type,
                error=f"Unknown job type: {job_type!r}",
            )
            return

        await crud.update_job_status(db, job_id, JOB_STATUS_RUNNING)
        event_logger.emit(
            EVENT_JOB_STARTED,
            trace_id=trace_id,
            stage="job",
            component=job_type,
            status="running",
            job_id=job_id,
            job_type=job_type,
        )
        logger.info("job.started", extra={"job_id": job_id, "job_type": job_type})

        start = time.monotonic()
        try:
            result = await handler.execute(payload)
            await crud.update_job_status(db, job_id, JOB_STATUS_COMPLETED, result=result)
            latency_ms = (time.monotonic() - start) * 1000
            event_logger.emit(
                EVENT_JOB_COMPLETED,
                trace_id=trace_id,
                stage="job",
                component=job_type,
                status="success",
                job_id=job_id,
                job_type=job_type,
                latency_ms=round(latency_ms, 2),
            )
            logger.info("job.completed", extra={"job_id": job_id, "job_type": job_type})
        except Exception as exc:
            error_msg = str(exc)
            await crud.update_job_status(db, job_id, JOB_STATUS_FAILED, error=error_msg)
            latency_ms = (time.monotonic() - start) * 1000
            event_logger.emit(
                EVENT_JOB_FAILED,
                trace_id=trace_id,
                stage="job",
                component=job_type,
                status="fail",
                job_id=job_id,
                job_type=job_type,
                error=error_msg,
                latency_ms=round(latency_ms, 2),
            )
            logger.error("job.failed", extra={"job_id": job_id, "job_type": job_type, "error": error_msg})

    async def _run_background(
        self,
        job_id: str,
        job_type: str,
        payload: dict[str, Any],
        trace_id: str = "",
    ) -> None:
        """
        Execute a job with its own isolated DB session (async / fire-and-forget path).
        """
        from app.db.postgres import _get_session_local

        session_factory = _get_session_local()
        async with session_factory() as db:
            try:
                await self._execute(db, job_id, job_type, payload, trace_id=trace_id)
                await db.commit()
            except Exception as exc:
                await db.rollback()
                logger.error(
                    "job.background_error",
                    extra={"job_id": job_id, "job_type": job_type, "error": str(exc)},
                )


# Module-level singleton
job_manager = JobManager()
