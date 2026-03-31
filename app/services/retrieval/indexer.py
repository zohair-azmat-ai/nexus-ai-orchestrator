"""
Qdrant Indexer — upserts document chunks and their vectors into Qdrant.
"""

from qdrant_client.models import PointStruct

from app.core.config import settings
from app.core.logger import get_logger
from app.db.qdrant import ensure_collection, get_qdrant_client
from app.services.retrieval.chunker import ChunkItem
from app.services.retrieval.embeddings import EMBEDDING_DIM

logger = get_logger(__name__)


class QdrantIndexer:
    async def index(
        self,
        document_id: str,
        chunks: list[ChunkItem],
        embeddings: list[list[float]],
        source: str,
        metadata: dict,
    ) -> None:
        """
        Upsert document chunks with their vectors into Qdrant.

        Args:
            document_id: Parent document identifier.
            chunks: Ordered list of ChunkItem objects.
            embeddings: One embedding vector per chunk (must match len(chunks)).
            source: Source label stored in the payload.
            metadata: Arbitrary metadata stored in the payload.
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"chunks/embeddings length mismatch: {len(chunks)} vs {len(embeddings)}"
            )

        collection = settings.qdrant_collection_name
        await ensure_collection(collection_name=collection, vector_size=EMBEDDING_DIM)

        points = [
            PointStruct(
                id=chunk.chunk_id,
                vector=embedding,
                payload={
                    "chunk_id": chunk.chunk_id,
                    "chunk_index": chunk.chunk_index,
                    "document_id": document_id,
                    "text": chunk.text,
                    "source": source,
                    "metadata": metadata,
                },
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]

        client = get_qdrant_client()
        await client.upsert(collection_name=collection, points=points, wait=True)

        logger.info(
            "indexer.upsert.done",
            extra={
                "document_id": document_id,
                "chunks": len(points),
                "collection": collection,
            },
        )


indexer = QdrantIndexer()
