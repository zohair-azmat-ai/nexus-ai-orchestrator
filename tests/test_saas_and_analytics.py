from datetime import datetime, timedelta
from pathlib import Path
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401
from app.db import crud
from app.db.models.notification import NotificationLog
from app.db.postgres import Base
from app.services.escalations.manager import escalation_workflow
from app.services.saas import plan_service


@pytest.fixture
async def db_session():
    temp_dir = Path(".pytest-local")
    temp_dir.mkdir(exist_ok=True)
    db_file = temp_dir / f"{uuid.uuid4()}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await engine.dispose()
    if db_file.exists():
        db_file.unlink()


@pytest.mark.asyncio
async def test_high_severity_auto_assignment_and_notification(db_session):
    conversation = await crud.create_conversation(db_session, "customer@example.com")

    case = await escalation_workflow.ensure_case(
        db_session,
        conversation_id=conversation.id,
        trace_id="trace-1",
        user_id="customer@example.com",
        escalation_reason="This is urgent and still not resolved.",
        latest_agent="escalation",
        latest_summary="Escalation summary",
        severity="high",
        note_author="escalation",
        note_type="agent",
    )

    notifications = await db_session.execute(select(NotificationLog))
    notification = notifications.scalar_one()

    assert case.assigned_to == "reviewer_default"
    assert case.status == "in_review"
    assert notification.case_id == case.id
    assert notification.channel == "email"


@pytest.mark.asyncio
async def test_plan_limit_blocks_after_monthly_quota(db_session):
    await crud.create_user(
        db_session,
        email="prospect@example.com",
        full_name="Prospect",
        password_hash="hash",
        role="user",
        plan="free",
    )

    for _ in range(50):
        await plan_service.record_ticket(db_session, user_id="prospect@example.com", plan="free")

    with pytest.raises(HTTPException) as exc_info:
        await plan_service.ensure_ticket_allowed(db_session, "prospect@example.com")

    assert exc_info.value.status_code == 429
    assert "Monthly ticket limit reached" in exc_info.value.detail


@pytest.mark.asyncio
async def test_analytics_summary_counts_and_response_time(db_session):
    conversation = await crud.create_conversation(db_session, "analytics@example.com")
    user_message = await crud.create_message(
        db_session,
        conversation_id=conversation.id,
        role="user",
        content="Need help with my account",
    )
    assistant_message = await crud.create_message(
        db_session,
        conversation_id=conversation.id,
        role="assistant",
        content="We are reviewing your issue.",
    )
    user_message.created_at = datetime.utcnow()
    assistant_message.created_at = user_message.created_at + timedelta(seconds=5)

    await crud.create_escalation_case(
        db_session,
        conversation_id=conversation.id,
        trace_id="trace-analytics",
        user_id="analytics@example.com",
        escalation_reason="Need help with my account",
        severity="medium",
        latest_agent="support",
        latest_summary="summary",
    )
    await db_session.commit()

    summary = await crud.get_analytics_summary(db_session)

    assert summary["total_tickets"] == 1
    assert summary["total_escalations"] == 1
    assert summary["escalation_rate"] == 100.0
    assert summary["avg_response_time_seconds"] == 5.0
