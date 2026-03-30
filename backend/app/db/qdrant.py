from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_client: AsyncQdrantClient | None = None


def get_qdrant_client() -> AsyncQdrantClient:
    """Return (or lazily create) the shared Qdrant async client."""
    global _client
    if _client is None:
        kwargs: dict = {"url": settings.qdrant_url}
        if settings.qdrant_api_key:
            kwargs["api_key"] = settings.qdrant_api_key
        _client = AsyncQdrantClient(**kwargs)
    return _client


async def check_qdrant_connection() -> bool:
    """Health-check helper: returns True if Qdrant is reachable."""
    try:
        client = get_qdrant_client()
        await client.get_collections()
        return True
    except (UnexpectedResponse, Exception) as exc:
        logger.warning("Qdrant health check failed", extra={"error": str(exc)})
        return False
