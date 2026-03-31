from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.db import crud
from app.db.postgres import get_db
from app.main import app


BASE_PAYLOAD = {
    "user_id": "escalation-user",
    "session_id": "escalation-session",
    "history": [],
    "metadata": {},
}


def _payload(message: str) -> dict:
    return {**BASE_PAYLOAD, "message": message}


async def _create_reviewer(email: str = "reviewer@example.com", password: str = "Password123!") -> str:
    async for db in get_db():
        user = await crud.create_user(
            db,
            email=email,
            full_name="Reviewer Example",
            password_hash=hash_password(password),
            role="reviewer",
            is_active=True,
        )
        await db.commit()
        return user.email
    raise RuntimeError("Unable to create reviewer")


async def _login_reviewer(client: AsyncClient, email: str = "reviewer@example.com", password: str = "Password123!") -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_trigger_escalation_tool_persists_case_when_db_available(override_db):
    from app.db import crud
    from app.db.postgres import get_db
    from app.services.tools.trigger_escalation import trigger_escalation_tool

    async for db in get_db():
        conversation = await crud.create_conversation(db, "tool-user")
        result = await trigger_escalation_tool.execute(
            db=db,
            user_id="tool-user",
            reason="legal concern",
            conversation_id=conversation.id,
            trace_id="trace-tool-escalation",
            latest_agent="escalation",
            latest_summary="Escalated due to legal concern.",
        )
        await db.commit()

        case = await crud.get_escalation_case(db, result["case_id"])
        notes = await crud.list_escalation_notes(db, result["case_id"])

    assert result["case_id"] is not None
    assert result["status"] == "open"
    assert case is not None
    assert case.severity == "critical"
    assert len(notes) == 1
    assert "legal concern" in notes[0].content.lower()


@pytest.mark.asyncio
async def test_escalation_crud_and_filters(override_db):
    from app.db import crud
    from app.db.postgres import get_db

    async for db in get_db():
        conv_a = await crud.create_conversation(db, "user-a")
        conv_b = await crud.create_conversation(db, "user-b")
        case_a = await crud.create_escalation_case(
            db,
            conversation_id=conv_a.id,
            trace_id="trace-a",
            user_id="user-a",
            escalation_reason="urgent request",
            severity="high",
            latest_agent="escalation",
            latest_summary="Needs a human review quickly.",
        )
        case_b = await crud.create_escalation_case(
            db,
            conversation_id=conv_b.id,
            trace_id="trace-b",
            user_id="user-b",
            escalation_reason="refund issue",
            severity="medium",
            latest_agent="support",
            latest_summary="Customer requested a billing review.",
        )
        await crud.assign_escalation_case(db, case_a.id, "reviewer-1", status="in_review")
        await crud.update_escalation_status(db, case_b.id, "resolved")
        await crud.add_escalation_note(
            db,
            case_id=case_a.id,
            author="system",
            note_type="system",
            content="Escalation case opened.",
        )
        await crud.add_escalation_note(
            db,
            case_id=case_a.id,
            author="reviewer-1",
            note_type="human",
            content="Investigating now.",
        )
        await db.commit()

        fetched = await crud.get_escalation_case(db, case_a.id)
        filtered = await crud.list_escalation_cases(db, status="in_review", assigned_to="reviewer-1")
        notes = await crud.list_escalation_notes(db, case_a.id)

    assert fetched is not None
    assert fetched.assigned_to == "reviewer-1"
    assert len(filtered) == 1
    assert filtered[0].id == case_a.id
    assert len(notes) == 2
    assert notes[1].author == "reviewer-1"


@pytest.mark.asyncio
async def test_chat_escalation_creates_case_and_enriches_response():
    await _create_reviewer()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        auth_headers = await _login_reviewer(client)
        response = await client.post(
            "/api/v1/chat",
            json=_payload("This is urgent and I need a human manager immediately"),
        )

        assert response.status_code == 200
        body = response.json()
        case_id = body["escalation_case_id"]
        case_response = await client.get(f"/api/v1/escalations/{case_id}", headers=auth_headers)
        notes_response = await client.get(f"/api/v1/escalations/{case_id}/notes", headers=auth_headers)

    assert body["selected_agent"] == "escalation"
    assert body["event_summary"]["escalated"] is True
    assert body["escalation_case_id"] is not None
    assert body["escalation_status"] == "open"
    assert case_response.status_code == 200
    assert case_response.json()["status"] == "open"
    assert notes_response.status_code == 200
    assert notes_response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_escalation_review_api_supports_list_assign_status_and_notes():
    await _create_reviewer()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        auth_headers = await _login_reviewer(client)
        chat_response = await client.post(
            "/api/v1/chat",
            json=_payload("Please escalate this billing complaint"),
        )
        case_id = chat_response.json()["escalation_case_id"]

        list_response = await client.get("/api/v1/escalations?status=open", headers=auth_headers)
        assign_response = await client.post(
            f"/api/v1/escalations/{case_id}/assign",
            json={"assigned_to": "reviewer-2", "actor": "lead-1", "move_to_in_review": True},
            headers=auth_headers,
        )
        status_response = await client.post(
            f"/api/v1/escalations/{case_id}/status",
            json={"status": "approved", "actor": "reviewer-2"},
            headers=auth_headers,
        )
        note_response = await client.post(
            f"/api/v1/escalations/{case_id}/notes",
            json={"author": "reviewer-2", "note_type": "human", "content": "Approved for follow-up."},
            headers=auth_headers,
        )
        notes_response = await client.get(f"/api/v1/escalations/{case_id}/notes", headers=auth_headers)

    assert list_response.status_code == 200
    assert list_response.json()["total"] >= 1
    assert assign_response.status_code == 200
    assert assign_response.json()["assigned_to"] == "reviewer-2"
    assert assign_response.json()["status"] == "in_review"
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "approved"
    assert note_response.status_code == 200
    assert note_response.json()["author"] == "reviewer-2"
    assert notes_response.status_code == 200
    assert notes_response.json()["total"] >= 2


@pytest.mark.asyncio
async def test_invalid_escalation_status_transition_returns_400():
    await _create_reviewer()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        auth_headers = await _login_reviewer(client)
        chat_response = await client.post(
            "/api/v1/chat",
            json=_payload("Escalate this complaint right now"),
        )
        case_id = chat_response.json()["escalation_case_id"]
        await client.post(
            f"/api/v1/escalations/{case_id}/status",
            json={"status": "approved", "actor": "reviewer-1"},
            headers=auth_headers,
        )
        invalid_response = await client.post(
            f"/api/v1/escalations/{case_id}/status",
            json={"status": "in_review", "actor": "reviewer-1"},
            headers=auth_headers,
        )

    assert invalid_response.status_code == 400
    assert "Invalid escalation status transition" in invalid_response.json()["detail"]


@pytest.mark.asyncio
async def test_escalation_observability_events_are_emitted():
    await _create_reviewer()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Correlation-ID": "trace-escalation-events"},
    ) as client:
        auth_headers = await _login_reviewer(client)
        chat_response = await client.post(
            "/api/v1/chat",
            json=_payload("This is urgent, security related, and needs escalation"),
        )
        case_id = chat_response.json()["escalation_case_id"]
        assert case_id
        await client.post(
            f"/api/v1/escalations/{case_id}/assign",
            json={"assigned_to": "reviewer-3", "actor": "lead-2", "move_to_in_review": True},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/escalations/{case_id}/status",
            json={"status": "approved", "actor": "reviewer-3"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/escalations/{case_id}/notes",
            json={"author": "reviewer-3", "note_type": "human", "content": "Captured final approval note."},
            headers=auth_headers,
        )
        trace_response = await client.get("/api/v1/observability/trace/trace-escalation-events")

    assert trace_response.status_code == 200
    event_types = {event["event_type"] for event in trace_response.json()["events"]}
    assert "escalation.case.created" in event_types
    assert "escalation.case.assigned" in event_types
    assert "escalation.case.status_changed" in event_types
    assert "escalation.note.added" in event_types
