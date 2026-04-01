"""
Semantic Search — queries Qdrant for document chunks relevant to a user query.

Flow: embed query → query_points → deserialize ScoredPoint payloads → return results.
"""

from app.core.config import settings
from app.core.logger import get_logger
from app.db.qdrant import get_qdrant_client
from app.services.retrieval.embeddings import embeddings_service

logger = get_logger(__name__)


class SemanticSearch:
    async def search(self, query: str, top_k: int | None = None) -> list[dict]:
        """
        Search for relevant document chunks via vector similarity.

        Returns a list of result dicts, each with:
            chunk_id, document_id, chunk_index, text, score, metadata, source

        Returns [] on any error (Qdrant down, missing API key, etc.) so the
        orchestrator can continue gracefully without retrieval context.
        """
        k = top_k or settings.rag_top_k
        collection = settings.qdrant_collection_name

        try:
            query_vector = await embeddings_service.embed_query(query)
        except ValueError as exc:
            logger.warning("search.embed_failed", extra={"reason": str(exc)})
            return []

        try:
            client = get_qdrant_client()
            response = await client.query_points(
                collection_name=collection,
                query=query_vector,
                limit=k,
                score_threshold=settings.rag_min_score,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:
            logger.warning(
                "search.qdrant_failed",
                extra={"collection": collection, "error": str(exc)},
            )
            return []

        results = []
        for point in response.points:
            payload = point.payload or {}
            results.append({
                "chunk_id": payload.get("chunk_id", str(point.id)),
                "document_id": payload.get("document_id", ""),
                "chunk_index": payload.get("chunk_index", 0),
                "text": payload.get("text", ""),
                "score": round(point.score, 4),
                "source": payload.get("source", ""),
                "metadata": payload.get("metadata", {}),
            })

        logger.info(
            "search.done",
            extra={"query_len": len(query), "top_k": k, "results": len(results), "collection": collection},
        )
        return results

    def format_context(self, results: list[dict]) -> str:
        """
        Format search results into a compact context block for LLM prompts.

        Each chunk is prefixed with its source and score so the model can
        judge relevance. Raw results are never dumped verbatim into the answer.
        """
        if not results:
            return ""

        parts = []
        for i, r in enumerate(results, 1):
            source_label = r.get("source") or r.get("document_id") or "unknown"
            parts.append(
                f"[{i}] (source: {source_label}, score: {r['score']})\n{r['text']}"
            )
        return "\n\n---\n\n".join(parts)


semantic_search = SemanticSearch()
