"""
Tests for Phase 4 Step 1 — async job system.

Covers:
  - JobRegistry: register, get, list, overwrite
  - CRUD: create_job, update_job_status, get_job_by_id, list_recent_jobs
  - JobManager: submit (inline mode), status lifecycle
  - MemorySummaryJob: execute with mocked DB and summarizer
  - DocumentIngestionJob: execute with mocked ingest_service
  - AnalyticsAggregationJob: execute returns metric snapshot
  - Job API endpoints: POST /jobs/ingest, POST /jobs/memory-summary, GET /jobs, GET /jobs/{job_id}
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_test_db(override_db_fixture) -> AsyncSession:
    """Get the current test DB session via the app's dependency override."""
    gen = app.dependency_overrides[__import__("app.db.postgres", fromlist=["get_db"]).get_db]()
    session = None
    async for s in gen:
        session = s
    return session


# ─── JobRegistry ─────────────────────────────────────────────────────────────

class TestJobRegistry:
    def setup_method(self):
        from app.services.jobs.registry import JobRegistry
        self.registry = JobRegistry()

    def _make_job(self, job_type="test_job"):
        from app.services.jobs.base import BaseJob

        class _DummyJob(BaseJob):
            async def execute(self_, payload):
                return {"ok": True}

        j = _DummyJob()
        j.job_type = job_type
        return j

    def test_register_and_get(self):
        job = self._make_job("alpha")
        self.registry.register(job)
        assert self.registry.get("alpha") is job

    def test_get_missing_returns_none(self):
        assert self.registry.get("nope") is None

    def test_list_job_types(self):
        self.registry.register(self._make_job("a"))
        self.registry.register(self._make_job("b"))
        types = self.registry.list_job_types()
        assert "a" in types
        assert "b" in types

    def test_overwrite(self):
        j1 = self._make_job("dup")
        j2 = self._make_job("dup")
        self.registry.register(j1)
        self.registry.register(j2)
        assert self.registry.get("dup") is j2

    def test_len_and_contains(self):
        self.registry.register(self._make_job("x"))
        assert len(self.registry) == 1
        assert "x" in self.registry
        assert "missing" not in self.registry

    def test_global_registry_has_3_jobs(self):
        import app.services.jobs  # noqa: F401
        from app.services.jobs.registry import job_registry
        assert len(job_registry) >= 3
        assert "memory_summary" in job_registry
        assert "document_ingestion" in job_registry
        assert "analytics_aggregation" in job_registry


# ─── CRUD ─────────────────────────────────────────────────────────────────────

class TestJobCrud:
    @pytest.mark.asyncio
    async def test_create_and_get_job(self, override_db):
        from app.db import crud
        from app.db.postgres import get_db

        async for db in get_db():
            job = await crud.create_job(db, "test_type", {"key": "value"})
            await db.commit()

            fetched = await crud.get_job_by_id(db, job.id)
            assert fetched is not None
            assert fetched.job_type == "test_type"
            assert fetched.status == "queued"
            assert fetched.payload_json == {"key": "value"}

    @pytest.mark.asyncio
    async def test_update_job_status_to_running(self, override_db):
        from app.db import crud
        from app.db.postgres import get_db

        async for db in get_db():
            job = await crud.create_job(db, "test_type", {})
            await crud.update_job_status(db, job.id, "running")
            await db.commit()

            fetched = await crud.get_job_by_id(db, job.id)
            assert fetched.status == "running"

    @pytest.mark.asyncio
    async def test_update_job_status_completed_with_result(self, override_db):
        from app.db import crud
        from app.db.postgres import get_db

        async for db in get_db():
            job = await crud.create_job(db, "test_type", {})
            await crud.update_job_status(db, job.id, "completed", result={"chunks": 3})
            await db.commit()

            fetched = await crud.get_job_by_id(db, job.id)
            assert fetched.status == "completed"
            assert fetched.result_json == {"chunks": 3}

    @pytest.mark.asyncio
    async def test_update_job_status_failed_with_error(self, override_db):
        from app.db import crud
        from app.db.postgres import get_db

        async for db in get_db():
            job = await crud.create_job(db, "test_type", {})
            await crud.update_job_status(db, job.id, "failed", error="something broke")
            await db.commit()

            fetched = await crud.get_job_by_id(db, job.id)
            assert fetched.status == "failed"
            assert fetched.error_text == "something broke"

    @pytest.mark.asyncio
    async def test_list_recent_jobs(self, override_db):
        from app.db import crud
        from app.db.postgres import get_db

        async for db in get_db():
            await crud.create_job(db, "type_a", {})
            await crud.create_job(db, "type_b", {})
            await crud.create_job(db, "type_a", {})
            await db.commit()

            all_jobs = await crud.list_recent_jobs(db, limit=10)
            assert len(all_jobs) == 3

            type_a = await crud.list_recent_jobs(db, limit=10, job_type="type_a")
            assert len(type_a) == 2
            assert all(j.job_type == "type_a" for j in type_a)

    @pytest.mark.asyncio
    async def test_get_job_by_id_missing_returns_none(self, override_db):
        from app.db import crud
        from app.db.postgres import get_db

        async for db in get_db():
            result = await crud.get_job_by_id(db, "nonexistent-id")
            assert result is None


# ─── JobManager (inline mode) ─────────────────────────────────────────────────

class TestJobManager:
    @pytest.mark.asyncio
    async def test_submit_inline_completed(self, override_db):
        from app.services.jobs.manager import JobManager
        from app.services.jobs.registry import JobRegistry
        from app.services.jobs.base import BaseJob
        from app.db.postgres import get_db

        # Fresh registry + manager for isolation
        registry = JobRegistry()

        class _SuccessJob(BaseJob):
            job_type = "success_job"
            async def execute(self_, payload):
                return {"done": True}

        registry.register(_SuccessJob())
        manager = JobManager()

        with patch("app.services.jobs.manager.job_registry", registry), \
             patch("app.core.config.settings.jobs_inline_mode", True):
            async for db in get_db():
                record = await manager.submit(db, "success_job", {"x": 1})
                await db.commit()

        assert record.status == "completed"
        assert record.result == {"done": True}
        assert record.job_type == "success_job"

    @pytest.mark.asyncio
    async def test_submit_inline_failed_on_exception(self, override_db):
        from app.services.jobs.manager import JobManager
        from app.services.jobs.registry import JobRegistry
        from app.services.jobs.base import BaseJob
        from app.db.postgres import get_db

        registry = JobRegistry()

        class _BrokenJob(BaseJob):
            job_type = "broken_job"
            async def execute(self_, payload):
                raise RuntimeError("job explosion")

        registry.register(_BrokenJob())
        manager = JobManager()

        with patch("app.services.jobs.manager.job_registry", registry), \
             patch("app.core.config.settings.jobs_inline_mode", True):
            async for db in get_db():
                record = await manager.submit(db, "broken_job", {})
                await db.commit()

        assert record.status == "failed"
        assert "job explosion" in (record.error or "")

    @pytest.mark.asyncio
    async def test_submit_unknown_job_type_fails(self, override_db):
        from app.services.jobs.manager import JobManager
        from app.services.jobs.registry import JobRegistry
        from app.db.postgres import get_db

        manager = JobManager()
        empty_registry = JobRegistry()

        with patch("app.services.jobs.manager.job_registry", empty_registry), \
             patch("app.core.config.settings.jobs_inline_mode", True):
            async for db in get_db():
                record = await manager.submit(db, "no_such_job", {})
                await db.commit()

        assert record.status == "failed"


# ─── Core job execute() tests ─────────────────────────────────────────────────

class TestDocumentIngestionJob:
    @pytest.mark.asyncio
    async def test_execute_calls_ingest_service(self):
        from app.services.jobs.document_ingestion_job import DocumentIngestionJob

        job = DocumentIngestionJob()
        mock_result = {"document_id": "doc-1", "chunks_created": 5, "collection_name": "nexus"}

        with patch("app.services.retrieval.ingest.ingest_service.ingest", new=AsyncMock(return_value=mock_result)):
            result = await job.execute({
                "text": "hello world",
                "source": "test",
                "metadata": {},
                "document_id": "doc-1",
            })

        assert result["document_id"] == "doc-1"
        assert result["chunks_created"] == 5


class TestAnalyticsAggregationJob:
    @pytest.mark.asyncio
    async def test_execute_returns_snapshot(self):
        from app.services.jobs.analytics_aggregation_job import AnalyticsAggregationJob

        job = AnalyticsAggregationJob()
        with patch("app.services.analytics.aggregator.get_all", return_value={"chat.received": 10}):
            result = await job.execute({})

        assert result["metrics"] == {"chat.received": 10}
        assert result["total_counters"] == 1
        assert "snapshot_at" in result


class TestMemorySummaryJob:
    @pytest.mark.asyncio
    async def test_execute_summarizes_and_upserts(self):
        from app.services.jobs.memory_summary_job import MemorySummaryJob

        job = MemorySummaryJob()

        mock_msg = MagicMock()
        mock_msg.role = "user"
        mock_msg.content = "hello"

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_session_factory = MagicMock(return_value=mock_session)

        with patch("app.services.jobs.memory_summary_job._get_session_local", return_value=mock_session_factory), \
             patch("app.db.crud.list_recent_messages", new=AsyncMock(return_value=[mock_msg])), \
             patch("app.db.crud.upsert_conversation_summary", new=AsyncMock()), \
             patch("app.services.memory.summarizer.conversation_summarizer.summarize", new=AsyncMock(return_value="nice summary")):
            result = await job.execute({"conversation_id": "c1", "user_id": "u1"})

        assert result["summary_text"] == "nice summary"
        assert result["message_count"] == 1
        assert result["conversation_id"] == "c1"

    @pytest.mark.asyncio
    async def test_execute_no_messages_returns_empty(self):
        from app.services.jobs.memory_summary_job import MemorySummaryJob

        job = MemorySummaryJob()

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_factory = MagicMock(return_value=mock_session)

        with patch("app.services.jobs.memory_summary_job._get_session_local", return_value=mock_session_factory), \
             patch("app.db.crud.list_recent_messages", new=AsyncMock(return_value=[])):
            result = await job.execute({"conversation_id": "c1", "user_id": "u1"})

        assert result["summary_text"] == ""
        assert result["message_count"] == 0


# ─── Job API endpoints ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_ingest_job_endpoint(override_db):
    """POST /jobs/ingest creates and runs a document ingestion job (inline mode)."""
    mock_ingest_result = {"document_id": "d1", "chunks_created": 3, "collection_name": "nexus"}
    with patch("app.services.retrieval.ingest.ingest_service.ingest", new=AsyncMock(return_value=mock_ingest_result)), \
         patch("app.core.config.settings.jobs_inline_mode", True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/jobs/ingest",
                json={"text": "some document text", "source": "test"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["job_type"] == "document_ingestion"
    assert body["status"] == "completed"
    assert body["result"]["document_id"] == "d1"
    assert "job_id" in body


@pytest.mark.asyncio
async def test_submit_memory_summary_job_endpoint(override_db):
    """POST /jobs/memory-summary creates a memory summary job."""
    mock_msg = MagicMock()
    mock_msg.role = "user"
    mock_msg.content = "test message"

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_factory = MagicMock(return_value=mock_session)

    with patch("app.services.jobs.memory_summary_job._get_session_local", return_value=mock_factory), \
         patch("app.db.crud.list_recent_messages", new=AsyncMock(return_value=[mock_msg])), \
         patch("app.db.crud.upsert_conversation_summary", new=AsyncMock()), \
         patch("app.services.memory.summarizer.conversation_summarizer.summarize", new=AsyncMock(return_value="summary text")), \
         patch("app.core.config.settings.jobs_inline_mode", True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/jobs/memory-summary",
                json={"conversation_id": "conv-1", "user_id": "u1"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["job_type"] == "memory_summary"
    assert "job_id" in body


@pytest.mark.asyncio
async def test_get_job_endpoint(override_db):
    """GET /jobs/{job_id} returns the job record."""
    mock_ingest_result = {"document_id": "d2", "chunks_created": 1, "collection_name": "nexus"}
    with patch("app.services.retrieval.ingest.ingest_service.ingest", new=AsyncMock(return_value=mock_ingest_result)), \
         patch("app.core.config.settings.jobs_inline_mode", True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create a job first
            create_resp = await client.post(
                "/api/v1/jobs/ingest",
                json={"text": "hello", "source": "test"},
            )
            job_id = create_resp.json()["job_id"]

            # Now fetch it
            get_resp = await client.get(f"/api/v1/jobs/{job_id}")

    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["job_id"] == job_id
    assert body["job_type"] == "document_ingestion"


@pytest.mark.asyncio
async def test_get_job_not_found(override_db):
    """GET /jobs/{job_id} returns 404 for unknown IDs."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/jobs/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_jobs_endpoint(override_db):
    """GET /jobs returns a list of jobs."""
    mock_ingest_result = {"document_id": "d3", "chunks_created": 2, "collection_name": "nexus"}
    with patch("app.services.retrieval.ingest.ingest_service.ingest", new=AsyncMock(return_value=mock_ingest_result)), \
         patch("app.core.config.settings.jobs_inline_mode", True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create two jobs
            await client.post("/api/v1/jobs/ingest", json={"text": "doc one", "source": "a"})
            await client.post("/api/v1/jobs/ingest", json={"text": "doc two", "source": "b"})

            list_resp = await client.get("/api/v1/jobs")

    assert list_resp.status_code == 200
    body = list_resp.json()
    assert "jobs" in body
    assert "total" in body
    assert body["total"] == 2
    assert all("job_id" in j for j in body["jobs"])


@pytest.mark.asyncio
async def test_list_jobs_filter_by_type(override_db):
    """GET /jobs?job_type=... filters results."""
    mock_ingest_result = {"document_id": "d4", "chunks_created": 1, "collection_name": "nexus"}
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_factory = MagicMock(return_value=mock_session)

    with patch("app.services.retrieval.ingest.ingest_service.ingest", new=AsyncMock(return_value=mock_ingest_result)), \
         patch("app.services.jobs.memory_summary_job._get_session_local", return_value=mock_factory), \
         patch("app.db.crud.list_recent_messages", new=AsyncMock(return_value=[])), \
         patch("app.core.config.settings.jobs_inline_mode", True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/jobs/ingest", json={"text": "doc", "source": "x"})
            await client.post("/api/v1/jobs/memory-summary", json={"conversation_id": "c1", "user_id": "u1"})
            resp = await client.get("/api/v1/jobs?job_type=document_ingestion")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["jobs"][0]["job_type"] == "document_ingestion"
