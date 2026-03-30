"""
Qdrant Indexer — upserts document chunks and their vectors into Qdrant.

Phase 1: logs only, no real Qdrant write (avoids hard dependency on running infra).
Phase 2: performs real upsert via qdrant_client.
"""

from app.core.logger import get_logger
from app.services.orchestrator.policies import retrieval_policy

logger = get_logger(__name__)


class QdrantIndexer:
    async def ensure_collection(self) -> None:
        """Create the Qdrant collection if it does not exist."""
        # Phase 2:
        # from app.db.qdrant import get_qdrant_client
        # from qdrant_client.models import Distance, VectorParams
        # client = get_qdrant_client()
        # await client.recreate_collection(...)
        logger.debug("indexer.ensure_collection.stub", extra={"collection": retrieval_policy.collection_name})

    async def index(
        self,
        document_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
        metadata: dict,
    ) -> None:
        """
        Upsert chunks + vectors into Qdrant.

        Phase 1: no-op with logging.
        Phase 2: build PointStruct list and call qdrant_client.upsert().
        """
        logger.info(
            "indexer.upsert.stub",
            extra={
                "document_id": document_id,
                "chunks": len(chunks),
                "collection": retrieval_policy.collection_name,
            },
        )


indexer = QdrantIndexer()
