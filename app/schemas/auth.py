from pydantic import BaseModel, Field


class AuthUserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    plan: str
    is_active: bool
    created_at: str
    updated_at: str


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserResponse
