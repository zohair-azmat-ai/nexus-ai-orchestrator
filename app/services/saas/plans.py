from dataclasses import dataclass
from datetime import datetime
from math import inf

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud

PLAN_FREE = "free"
PLAN_PRO = "pro"
PLAN_TEAM = "team"

PLAN_LIMITS: dict[str, float] = {
    PLAN_FREE: 50,
    PLAN_PRO: 500,
    PLAN_TEAM: inf,
}


@dataclass
class PlanDecision:
    user_key: str
    plan: str
    monthly_limit: int | None
    current_usage: int


class PlanService:
    def normalize_user_key(self, user_id: str) -> str:
        return user_id.strip().lower()

    def current_period_key(self) -> str:
        return datetime.utcnow().strftime("%Y-%m")

    async def resolve_plan(self, db: AsyncSession, user_id: str) -> str:
        normalized = self.normalize_user_key(user_id)
        user = await crud.get_user_by_id(db, normalized)
        if user is None and "@" in normalized:
            user = await crud.get_user_by_email(db, normalized)
        if user is None:
            return PLAN_FREE
        return (user.plan or PLAN_FREE).lower()

    async def get_plan_decision(self, db: AsyncSession, user_id: str) -> PlanDecision:
        user_key = self.normalize_user_key(user_id)
        plan = await self.resolve_plan(db, user_key)
        period_key = self.current_period_key()
        usage = await crud.get_ticket_usage(db, user_key=user_key, period_key=period_key)
        monthly_limit = PLAN_LIMITS.get(plan, PLAN_LIMITS[PLAN_FREE])
        return PlanDecision(
            user_key=user_key,
            plan=plan,
            monthly_limit=None if monthly_limit == inf else int(monthly_limit),
            current_usage=usage.ticket_count if usage else 0,
        )

    async def ensure_ticket_allowed(self, db: AsyncSession, user_id: str) -> PlanDecision:
        decision = await self.get_plan_decision(db, user_id)
        if decision.monthly_limit is not None and decision.current_usage >= decision.monthly_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Monthly ticket limit reached for the {decision.plan} plan. "
                    "Upgrade your plan or wait for the next billing cycle."
                ),
            )
        return decision

    async def record_ticket(self, db: AsyncSession, *, user_id: str, plan: str) -> None:
        await crud.increment_ticket_usage(
            db,
            user_key=self.normalize_user_key(user_id),
            period_key=self.current_period_key(),
            plan=plan,
        )


plan_service = PlanService()
