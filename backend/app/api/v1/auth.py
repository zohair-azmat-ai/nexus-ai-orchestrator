from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.db.postgres import get_db
from app.schemas.auth import AuthUserResponse, LoginRequest, LoginResponse
from app.schemas.common import ErrorResponse
from app.services.auth import auth_manager

router = APIRouter()


def _user_to_response(user) -> AuthUserResponse:
    return AuthUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    responses={401: {"model": ErrorResponse}},
    tags=["Auth"],
)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    user = await auth_manager.authenticate_user(db, email=request.email, password=request.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    token_payload = auth_manager.build_login_response(user)
    return LoginResponse(
        access_token=token_payload["access_token"],
        token_type=token_payload["token_type"],
        expires_in=token_payload["expires_in"],
        user=_user_to_response(token_payload["user"]),
    )


@router.get(
    "/auth/me",
    response_model=AuthUserResponse,
    responses={401: {"model": ErrorResponse}},
    tags=["Auth"],
)
async def get_me(current_user=Depends(get_current_user)) -> AuthUserResponse:
    return _user_to_response(current_user)
