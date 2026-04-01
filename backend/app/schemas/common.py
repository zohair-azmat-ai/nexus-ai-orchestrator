from pydantic import BaseModel, Field
from datetime import datetime


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DependencyStatus(BaseModel):
    status: str
    available: bool
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class ReadinessResponse(HealthResponse):
    dependencies: dict[str, DependencyStatus] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    correlation_id: str | None = None
