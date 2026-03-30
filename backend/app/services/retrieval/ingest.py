"""
Ingest Service — entry point for adding documents to the RAG pipeline.

Flow: raw content → chunker → embedder → indexer → Qdrant
"""

from app.core.ids import generate_id
from app.core.logger import get_logger
from app.services.retrieval.chunker import chunker
from app.services.retrieval.embeddings import embeddings_service
from app.services.retrieval.indexer import indexer

logger = get_logger(__name__)


class IngestService:
    async def ingest(self, source: str, content: str, metadata: dict) -> dict:
        """
        Ingest raw text content into the retrieval system.

        Returns a summary dict with document_id and chunks_created.
        """
        document_id = generate_id()
        logger.info("ingest.start", extra={"document_id": document_id, "source": source})

        # Step 1: chunk
        chunks = await chunker.chunk(content)
        logger.info("ingest.chunked", extra={"document_id": document_id, "chunks": len(chunks)})

        # Step 2: embed
        embeddings = await embeddings_service.embed(chunks)
        logger.info("ingest.embedded", extra={"document_id": document_id, "vectors": len(embeddings)})

        # Step 3: index into Qdrant
        await indexer.index(document_id=document_id, chunks=chunks, embeddings=embeddings, metadata=metadata)
        logger.info("ingest.indexed", extra={"document_id": document_id})

        return {"document_id": document_id, "chunks_created": len(chunks)}


ingest_service = IngestService()
