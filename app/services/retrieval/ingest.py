"""
Ingest Service — orchestrates the full document ingestion pipeline.

Flow: text → chunk → embed → upsert to Qdrant
"""

from app.core.ids import generate_id
from app.core.logger import get_logger
from app.services.retrieval.chunker import chunker
from app.services.retrieval.embeddings import embeddings_service
from app.services.retrieval.indexer import indexer

logger = get_logger(__name__)


class IngestService:
    async def ingest(
        self,
        text: str,
        source: str,
        metadata: dict,
        document_id: str | None = None,
    ) -> dict:
        """
        Run the full ingestion pipeline for a text document.

        Args:
            text: The raw text content to ingest.
            source: Source label (e.g. "docs", "kb", "url").
            metadata: Arbitrary metadata stored alongside each chunk.
            document_id: Optional caller-supplied ID. Auto-generated if None.

        Returns:
            dict with document_id, chunks_created, collection_name.

        Raises:
            ValueError: If OPENAI_API_KEY is not configured.
        """
        doc_id = document_id or generate_id()
        logger.info("ingest.start", extra={"document_id": doc_id, "source": source, "text_len": len(text)})

        # Step 1: chunk
        chunks = chunker.chunk(text, doc_id)
        if not chunks:
            logger.warning("ingest.no_chunks", extra={"document_id": doc_id})
            return {"document_id": doc_id, "chunks_created": 0, "collection_name": ""}

        logger.info("ingest.chunked", extra={"document_id": doc_id, "chunks": len(chunks)})

        # Step 2: embed — raises ValueError if API key is missing
        texts = [c.text for c in chunks]
        embeddings = await embeddings_service.embed(texts)
        logger.info("ingest.embedded", extra={"document_id": doc_id, "vectors": len(embeddings)})

        # Step 3: upsert into Qdrant
        from app.core.config import settings
        await indexer.index(
            document_id=doc_id,
            chunks=chunks,
            embeddings=embeddings,
            source=source,
            metadata=metadata,
        )
        logger.info("ingest.indexed", extra={"document_id": doc_id, "collection": settings.qdrant_collection_name})

        return {
            "document_id": doc_id,
            "chunks_created": len(chunks),
            "collection_name": settings.qdrant_collection_name,
        }


ingest_service = IngestService()
