"""
Tests for the /api/v1/ingest endpoint.

Qdrant and OpenAI are mocked so tests run without live services.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

INGEST_PAYLOAD = {
    "text": "Nexus AI is a multi-agent RAG orchestration platform. "
            "It supports memory, retrieval, and multi-agent coordination.",
    "source": "test-docs",
    "metadata": {"category": "platform", "version": "2"},
}

FAKE_EMBEDDING = [0.1] * 1536


def _embed_side_effect(texts: list[str]) -> list[list[float]]:
    """Return one fake embedding per input text — matches actual chunk count."""
    return [FAKE_EMBEDDING for _ in texts]


def _mock_qdrant_client():
    """Build a mock AsyncQdrantClient that behaves like a healthy instance."""
    client = MagicMock()
    client.get_collection = AsyncMock(side_effect=Exception("collection not found"))
    client.create_collection = AsyncMock(return_value=None)
    client.upsert = AsyncMock(return_value=None)
    query_resp = MagicMock()
    query_resp.points = []
    client.query_points = AsyncMock(return_value=query_resp)
    return client


def _ingest_patches(mock_client):
    return (
        patch(
            "app.services.retrieval.embeddings.EmbeddingsService.embed",
            new_callable=AsyncMock,
            side_effect=_embed_side_effect,
        ),
        patch("app.db.qdrant.get_qdrant_client", return_value=mock_client),
        patch("app.services.retrieval.indexer.get_qdrant_client", return_value=mock_client),
        patch("app.services.retrieval.indexer.ensure_collection", new_callable=AsyncMock),
    )


@pytest.mark.asyncio
async def test_ingest_returns_200():
    mock_client = _mock_qdrant_client()
    p1, p2, p3, p4 = _ingest_patches(mock_client)
    with p1, p2, p3, p4:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/ingest", json=INGEST_PAYLOAD)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ingest_response_shape():
    mock_client = _mock_qdrant_client()
    p1, p2, p3, p4 = _ingest_patches(mock_client)
    with p1, p2, p3, p4:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/ingest", json=INGEST_PAYLOAD)

    data = response.json()
    assert data["status"] == "ok"
    assert "document_id" in data
    assert "chunks_created" in data
    assert "collection_name" in data
    assert data["chunks_created"] > 0
    assert len(data["document_id"]) > 0


@pytest.mark.asyncio
async def test_ingest_with_explicit_document_id():
    mock_client = _mock_qdrant_client()
    p1, p2, p3, p4 = _ingest_patches(mock_client)
    custom_id = "my-doc-abc-123"
    with p1, p2, p3, p4:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ingest",
                json={**INGEST_PAYLOAD, "document_id": custom_id},
            )
    data = response.json()
    assert data["document_id"] == custom_id


@pytest.mark.asyncio
async def test_ingest_returns_400_when_api_key_missing():
    """Ingest must return 400 if OPENAI_API_KEY is not set."""
    with patch("app.services.retrieval.embeddings.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        mock_settings.openai_embedding_model = "text-embedding-3-small"

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/ingest", json=INGEST_PAYLOAD)

    assert response.status_code == 400
    assert "OPENAI_API_KEY" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ingest_calls_embeddings_once_per_chunk():
    mock_client = _mock_qdrant_client()
    with (
        patch(
            "app.services.retrieval.embeddings.EmbeddingsService.embed",
            new_callable=AsyncMock,
            side_effect=_embed_side_effect,
        ) as mock_embed,
        patch("app.db.qdrant.get_qdrant_client", return_value=mock_client),
        patch("app.services.retrieval.indexer.get_qdrant_client", return_value=mock_client),
        patch("app.services.retrieval.indexer.ensure_collection", new_callable=AsyncMock),
    ):
        short_payload = {**INGEST_PAYLOAD, "text": "Short document."}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/ingest", json=short_payload)

    data = response.json()
    assert data["chunks_created"] == 1
    mock_embed.assert_called_once()
    called_texts = mock_embed.call_args[0][0]
    assert len(called_texts) == 1
