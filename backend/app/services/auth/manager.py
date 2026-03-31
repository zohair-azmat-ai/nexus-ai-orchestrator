from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db import crud
from app.db.models.user import User


class AuthManager:
    async def authenticate_user(self, db: AsyncSession, *, email: str, password: str) -> User | None:
        user = await crud.get_user_by_email(db, email)
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def build_login_response(self, user: User) -> dict:
        return {
            "access_token": create_access_token(user.id, user.role),
            "token_type": "bearer",
            "expires_in": settings.auth_access_token_expire_seconds,
            "user": user,
        }

    async def ensure_dev_users(self, db: AsyncSession) -> None:
        if not settings.auth_bootstrap_dev_users or settings.app_env.lower() not in {"dev", "development", "local"}:
            return

        await crud.create_or_update_user(
            db,
            email=settings.auth_dev_admin_email,
            full_name="Nexus Admin",
            password_hash=hash_password(settings.auth_dev_admin_password),
            role="admin",
            is_active=True,
        )
        await crud.create_or_update_user(
            db,
            email=settings.auth_dev_reviewer_email,
            full_name="Nexus Reviewer",
            password_hash=hash_password(settings.auth_dev_reviewer_password),
            role="reviewer",
            is_active=True,
        )


auth_manager = AuthManager()
