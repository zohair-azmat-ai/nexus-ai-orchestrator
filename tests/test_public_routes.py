from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.schemas.pipeline import PipelineResult


def test_public_routes_and_analytics_smoke(monkeypatch):
    smoke_dir = Path(".pytest-local")
    smoke_dir.mkdir(exist_ok=True)

    settings.database_url = "sqlite+aiosqlite:///./.pytest-local/smoke.db"
    settings.app_env = "development"

    import app.db.postgres as postgres

    postgres._engine = None
    postgres._session_local = None

    from app.api.v1 import chat as chat_api
    from app.main import app

    async def fake_pipeline(request, db=None, conversation_id=None):
        return PipelineResult(
            correlation_id="corr-1",
            trace_id="trace-1",
            answer="Your issue has been captured.",
            selected_agent="support",
            execution_mode="single_step",
            executed_steps_count=1,
            skipped_steps_count=0,
            final_agent="support",
            memory_used=False,
            retrieval_used=False,
            confidence=0.91,
            escalation_case_id=None,
            escalation_status=None,
        )

    monkeypatch.setattr(chat_api, "run_pipeline", fake_pipeline)

    with TestClient(app) as client:
        report = client.get("/report")
        analytics_page = client.get("/analytics")
        chat_response = client.post(
            "/api/v1/chat",
            json={
                "user_id": "smoke@example.com",
                "session_id": "session-1",
                "message": "Need help with billing. This issue should be prioritized soon.",
            },
        )
        analytics_api = client.get("/api/v1/analytics/summary")

    assert report.status_code == 200
    assert "Report an issue to Nexus AI" in report.text
    assert analytics_page.status_code == 200
    assert "Nexus AI analytics dashboard" in analytics_page.text
    assert chat_response.status_code == 200
    assert analytics_api.status_code == 200
    assert analytics_api.json()["total_tickets"] >= 1
