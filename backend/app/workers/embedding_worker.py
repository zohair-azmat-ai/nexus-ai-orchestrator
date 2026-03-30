"""
Embedding Worker — async background worker for batch embedding jobs.

Phase 1: stub placeholder.
Phase 4: consumes from a task queue (e.g. Redis/ARQ) and runs batch embeddings.
"""

from app.core.logger import get_logger

logger = get_logger(__name__)


async def run_embedding_job(document_ids: list[str]) -> None:
    """
    Process pending embedding jobs for the given document IDs.

    Phase 4: pull from task queue, embed in batches, upsert to Qdrant.
    """
    logger.info("embedding_worker.stub", extra={"document_count": len(document_ids)})
