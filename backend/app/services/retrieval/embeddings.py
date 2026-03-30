"""
Embeddings Service — converts text chunks into dense vector representations.

Phase 1: stub that returns zero vectors.
Phase 2: calls OpenAI text-embedding-3-small (or local model).
"""

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

EMBEDDING_DIM = 1536  # text-embedding-3-small dimension


class EmbeddingsService:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of text chunks.

        Returns a list of float vectors, one per input text.
        Phase 1: returns zero vectors of the correct dimension.
        Phase 2: calls OpenAI embeddings API.
        """
        if not texts:
            return []

        # Phase 2: replace with real OpenAI call
        # from app.services.llm.openai_client import openai_client
        # response = await openai_client.client.embeddings.create(...)

        logger.debug("embeddings.stub", extra={"count": len(texts), "model": settings.openai_embedding_model})
        return [[0.0] * EMBEDDING_DIM for _ in texts]

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        vectors = await self.embed([query])
        return vectors[0] if vectors else [0.0] * EMBEDDING_DIM


embeddings_service = EmbeddingsService()
