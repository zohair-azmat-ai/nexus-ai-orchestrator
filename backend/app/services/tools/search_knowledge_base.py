"""
SearchKnowledgeBase tool — wraps the semantic search service.

Agents can call this to perform on-demand retrieval separate from the
pipeline's automatic retrieval stage, or to search with a refined query.
"""

from typing import Any

from app.services.tools.base_tool import BaseTool


class SearchKnowledgeBaseTool(BaseTool):
    name = "search_knowledge_base"
    description = (
        "Performs semantic search over indexed documents in the knowledge base. "
        "Returns matching chunks with scores and a formatted context block."
    )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "query": "str — the search query",
            "top_k": "int (optional, default uses settings.rag_top_k) — max results",
        }

    async def execute(self, **kwargs) -> dict[str, Any]:
        from app.services.retrieval.search import semantic_search

        query: str = kwargs["query"]
        top_k: int | None = kwargs.get("top_k")

        results = await semantic_search.search(query, top_k=top_k)
        context = semantic_search.format_context(results) if results else ""

        return {
            "results": results,
            "context": context,
            "count": len(results),
            "query": query,
        }


search_knowledge_base_tool = SearchKnowledgeBaseTool()
