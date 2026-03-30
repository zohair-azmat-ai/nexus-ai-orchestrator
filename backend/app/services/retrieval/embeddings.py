"""
Embeddings Service — converts text into dense vector representations via OpenAI.

Fails with a clear ValueError if OPENAI_API_KEY is not configured so callers
can surface a meaningful error instead of silently returning zero vectors.
"""

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# Dimension for text-embedding-3-small. Used as a fallback constant.
EMBEDDING_DIM = 1536


class EmbeddingsService:
    def _require_api_key(self) -> None:
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is not configured. "
                "Set it in your .env file to enable embeddings."
            )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of text strings via the OpenAI embeddings API.

        Returns one float vector per input text.
        Raises ValueError if OPENAI_API_KEY is missing.
        """
        if not texts:
            return []

        self._require_api_key()

        from app.services.llm.openai_client import openai_client

        logger.debug(
            "embeddings.request",
            extra={"count": len(texts), "model": settings.openai_embedding_model},
        )

        vectors = await openai_client.embed(texts)

        logger.debug(
            "embeddings.done",
            extra={"count": len(vectors), "dim": len(vectors[0]) if vectors else 0},
        )
        return vectors

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query string. Returns a single vector."""
        vectors = await self.embed([query])
        return vectors[0] if vectors else [0.0] * EMBEDDING_DIM


embeddings_service = EmbeddingsService()
