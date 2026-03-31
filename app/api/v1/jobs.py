"""
Jobs API — submit and inspect background jobs.

Endpoints:
  POST /jobs/ingest           — queue a document ingestion job
  POST /jobs/memory-summary   — queue a memory summary job
  GET  /jobs/{job_id}         — get job status by ID
  GET  /jobs                  — list recent jobs
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.db import crud
from app.db.postgres import get_db
from app.schemas.common import ErrorResponse
from app.schemas.jobs import JobIngestRequest, JobMemorySummaryRequest, JobResponse, JobListResponse
from app.services.jobs.manager import job_manager
from app.services.jobs.types import JOB_TYPE_DOCUMENT_INGESTION, JOB_TYPE_MEMORY_SUMMARY

router = APIRouter()
logger = get_logger(__name__)


def _row_to_response(job) -> JobResponse:
    return JobResponse(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
        payload=job.payload_json or {},
        result=job.result_json,
        error=job.error_text,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )


def _record_to_response(record) -> JobResponse:
    return JobResponse(
        job_id=record.job_id,
        job_type=record.job_type,
        status=record.status,
        payload=record.payload,
        result=record.result,
        error=record.error,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
    )


@router.post(
    "/jobs/ingest",
    response_model=JobResponse,
    responses={500: {"model": ErrorResponse}},
    tags=["Jobs"],
)
async def submit_ingest_job(
    request: JobIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """
    Queue a document ingestion job.

    When jobs_inline_mode=True (default), runs synchronously and returns the
    completed job record. When False, returns immediately with status 'queued'.
    """
    try:
        payload = {
            "text": request.text,
            "source": request.source,
            "metadata": request.metadata,
            "document_id": request.document_id,
        }
        record = await job_manager.submit(db, JOB_TYPE_DOCUMENT_INGESTION, payload)
        await db.commit()
        return _record_to_response(record)
    except Exception as exc:
        await db.rollback()
        logger.error("jobs.ingest.error", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/jobs/memory-summary",
    response_model=JobResponse,
    responses={500: {"model": ErrorResponse}},
    tags=["Jobs"],
)
async def submit_memory_summary_job(
    request: JobMemorySummaryRequest,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Queue a memory summary job for the given conversation."""
    try:
        payload = {
            "conversation_id": request.conversation_id,
            "user_id": request.user_id,
        }
        record = await job_manager.submit(db, JOB_TYPE_MEMORY_SUMMARY, payload)
        await db.commit()
        return _record_to_response(record)
    except Exception as exc:
        await db.rollback()
        logger.error("jobs.memory_summary.error", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    responses={404: {"model": ErrorResponse}},
    tags=["Jobs"],
)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Retrieve a background job by its ID."""
    job = await crud.get_job_by_id(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")
    return _row_to_response(job)


@router.get(
    "/jobs",
    response_model=JobListResponse,
    tags=["Jobs"],
)
async def list_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    job_type: str | None = Query(default=None, description="Filter by job type"),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """List recent background jobs, newest first."""
    jobs = await crud.list_recent_jobs(db, limit=limit, job_type=job_type)
    return JobListResponse(
        jobs=[_row_to_response(j) for j in jobs],
        total=len(jobs),
    )
