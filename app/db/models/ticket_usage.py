import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class TicketUsage(Base):
    __tablename__ = "ticket_usage"
    __table_args__ = (
        UniqueConstraint("user_key", "period_key", name="uq_ticket_usage_user_period"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    period_key: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    ticket_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now, nullable=False)
