"""
Semantic Search — queries Qdrant for documents relevant to a user query.

Phase 1: stub returning an empty list.
Phase 2: embed query → Qdrant search → format results.
"""

from app.core.logger import get_logger
from app.services.orchestrator.policies import retrieval_policy
from app.services.retrieval.embeddings import embeddings_service

logger = get_logger(__name__)


class SemanticSearch:
    async def search(self, query: str, top_k: int | None = None) -> list[dict]:
        """
        Search for relevant document chunks.

        Returns a list of result dicts with keys: text, score, metadata.
        Phase 1: always returns [].
        Phase 2: real vector search via Qdrant.
        """
        k = top_k or retrieval_policy.top_k

        # Phase 2:
        # query_vector = await embeddings_service.embed_query(query)
        # client = get_qdrant_client()
        # results = await client.search(collection_name=..., query_vector=query_vector, limit=k)

        logger.debug("search.stub", extra={"query_len": len(query), "top_k": k})
        return []

    async def format_results(self, raw_results: list) -> str:
        """Convert Qdrant results into a context string for the LLM prompt."""
        if not raw_results:
            return ""
        return "\n\n".join(r.get("text", "") for r in raw_results)


semantic_search = SemanticSearch()
