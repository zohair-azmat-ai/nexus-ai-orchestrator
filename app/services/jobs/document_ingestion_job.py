"""
DocumentIngestionJob — async wrapper around the ingest pipeline.

Payload keys:
  text        : str          — raw document text
  source      : str          — source label (e.g. "docs", "kb")
  metadata    : dict         — arbitrary metadata stored with each chunk
  document_id : str | None   — optional caller-supplied document ID
"""

from typing import Any

from app.services.jobs.base import BaseJob
from app.services.jobs.types import JOB_TYPE_DOCUMENT_INGESTION
from app.core.logger import get_logger

logger = get_logger(__name__)


class DocumentIngestionJob(BaseJob):
    job_type = JOB_TYPE_DOCUMENT_INGESTION

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        from app.services.retrieval.ingest import ingest_service

        text: str = payload["text"]
        source: str = payload.get("source", "")
        metadata: dict = payload.get("metadata", {})
        document_id: str | None = payload.get("document_id")

        result = await ingest_service.ingest(
            text=text,
            source=source,
            metadata=metadata,
            document_id=document_id,
        )
        logger.info(
            "document_ingestion_job.done",
            extra={
                "document_id": result["document_id"],
                "chunks_created": result["chunks_created"],
            },
        )
        return result


document_ingestion_job = DocumentIngestionJob()
