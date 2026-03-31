from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = Field(default="nexus-ai")
    app_env: Literal["development", "test", "staging", "production"] = Field(default="development")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)

    # Database
    database_url: str = Field(default="postgresql+psycopg://nexus:nexus_secret@localhost:5432/nexus_db")

    # Qdrant
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_api_key: str = Field(default="")
    qdrant_collection_name: str = Field(default="nexus_documents")

    # OpenAI
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o")
    openai_embedding_model: str = Field(default="text-embedding-3-small")

    # RAG
    rag_chunk_size: int = Field(default=512)
    rag_chunk_overlap: int = Field(default=64)
    rag_top_k: int = Field(default=5)
    rag_min_score: float = Field(default=0.4)

    # Memory
    memory_summary_trigger_count: int = Field(default=10)
    memory_recent_message_limit: int = Field(default=5)
    memory_enable_llm_summarization: bool = Field(default=True)

    # Background Jobs
    jobs_inline_mode: bool = Field(default=True, description="Run jobs synchronously inline (set False for true async)")
    jobs_max_concurrency: int = Field(default=10, description="Max concurrent background jobs (async mode)")
    enable_async_memory_summary: bool = Field(default=False, description="Queue memory summary as a background job")
    enable_async_ingest: bool = Field(default=False, description="Queue document ingestion as a background job")

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    # CORS
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Auth
    auth_secret_key: str = Field(default="nexus-ai-dev-secret-key")
    auth_access_token_expire_seconds: int = Field(default=60 * 60 * 8)
    auth_bootstrap_dev_users: bool = Field(default=True)
    auth_dev_admin_email: str = Field(default="admin@nexus.local")
    auth_dev_admin_password: str = Field(default="AdminPass123!")
    auth_dev_reviewer_email: str = Field(default="reviewer@nexus.local")
    auth_dev_reviewer_password: str = Field(default="ReviewerPass123!")

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_app_env(cls, value: str):
        if isinstance(value, str):
            normalized = value.strip().lower()
            alias_map = {
                "dev": "development",
                "local": "development",
                "testing": "test",
                "prod": "production",
            }
            return alias_map.get(normalized, normalized)
        return value

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def normalize_cors_allowed_origins(cls, value):
        if value in (None, "", []):
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def validate_runtime_configuration(self) -> list[str]:
        errors: list[str] = []

        if self.is_production:
            if self.debug:
                errors.append("DEBUG must be false when APP_ENV=production.")
            if not self.database_url:
                errors.append("DATABASE_URL is required in production.")
            if not self.qdrant_url:
                errors.append("QDRANT_URL is required in production.")
            if not self.openai_api_key:
                errors.append("OPENAI_API_KEY is required in production.")
            if not self.auth_secret_key or self.auth_secret_key == "nexus-ai-dev-secret-key":
                errors.append(
                    "AUTH_SECRET_KEY must be set to a strong non-default secret in production."
                )
            elif len(self.auth_secret_key) < 32:
                errors.append("AUTH_SECRET_KEY must be at least 32 characters long in production.")
            if not self.cors_allowed_origins:
                errors.append("CORS_ALLOWED_ORIGINS must include at least one allowed origin in production.")

        if self.auth_access_token_expire_seconds <= 0:
            errors.append("AUTH_ACCESS_TOKEN_EXPIRE_SECONDS must be greater than zero.")

        return errors


settings = Settings()
