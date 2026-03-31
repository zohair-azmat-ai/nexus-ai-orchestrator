from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, VectorParams

from app.core.config import settings
from app.core.logger import get_logger, sanitize_log_value

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


async def ensure_collection(
    collection_name: str,
    vector_size: int = 1536,
    distance: Distance = Distance.COSINE,
) -> None:
    """
    Create the Qdrant collection if it does not already exist.

    Safe to call on every ingest — it is a no-op when the collection exists.
    """
    client = get_qdrant_client()
    try:
        await client.get_collection(collection_name)
        logger.debug("qdrant.collection_exists", extra={"collection": collection_name})
    except Exception:
        # Collection does not exist — create it
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=distance),
        )
        logger.info(
            "qdrant.collection_created",
            extra={"collection": collection_name, "vector_size": vector_size, "distance": distance.value},
        )


async def check_qdrant_connection() -> bool:
    """Health-check helper: returns True if Qdrant is reachable."""
    try:
        client = get_qdrant_client()
        await client.get_collections()
        return True
    except (UnexpectedResponse, Exception) as exc:
        logger.warning(
            "qdrant.health_check_failed",
            extra={"error_type": exc.__class__.__name__, "detail": sanitize_log_value(str(exc))},
        )
        return False
