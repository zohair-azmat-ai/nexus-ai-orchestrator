from fastapi import APIRouter

from app.core.logger import get_logger
from app.schemas.ingest import IngestRequest, IngestResponse
from app.services.retrieval.ingest import ingest_service

router = APIRouter()
logger = get_logger(__name__)


@router.post("/ingest", response_model=IngestResponse, tags=["Retrieval"])
async def ingest_document(request: IngestRequest) -> IngestResponse:
    """
    Ingest a document into the retrieval pipeline.

    Chunks the content, generates embeddings, and indexes into Qdrant.
    Phase 1: chunking and indexing are stubs — no real Qdrant writes.
    """
    logger.info("ingest.request", extra={"source": request.source, "content_len": len(request.content)})

    result = await ingest_service.ingest(
        source=request.source,
        content=request.content,
        metadata=request.metadata,
    )

    return IngestResponse(
        status="ok",
        document_id=result["document_id"],
        chunks_created=result["chunks_created"],
    )
