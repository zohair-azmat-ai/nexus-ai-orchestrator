from fastapi import APIRouter, HTTPException

from app.core.ids import get_correlation_id
from app.core.logger import get_logger
from app.schemas.common import ErrorResponse
from app.schemas.ingest import IngestRequest, IngestResponse
from app.services.retrieval.ingest import ingest_service

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/ingest",
    response_model=IngestResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    tags=["Retrieval"],
)
async def ingest_document(request: IngestRequest) -> IngestResponse:
    """
    Ingest a document into the retrieval pipeline.

    The text is chunked, embedded via OpenAI, and indexed into Qdrant.
    Requires OPENAI_API_KEY and a running Qdrant instance.
    """
    correlation_id = get_correlation_id()
    logger.info(
        "ingest.request",
        extra={
            "correlation_id": correlation_id,
            "document_id": request.document_id,
            "source": request.source,
            "text_len": len(request.text),
        },
    )

    try:
        result = await ingest_service.ingest(
            text=request.text,
            source=request.source,
            metadata=request.metadata,
            document_id=request.document_id,
        )
    except ValueError as exc:
        # Missing API key or configuration error
        logger.warning("ingest.config_error", extra={"error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("ingest.error", extra={"error": str(exc), "correlation_id": correlation_id})
        raise HTTPException(status_code=500, detail=str(exc))

    return IngestResponse(
        status="ok",
        document_id=result["document_id"],
        chunks_created=result["chunks_created"],
        collection_name=result["collection_name"],
    )
