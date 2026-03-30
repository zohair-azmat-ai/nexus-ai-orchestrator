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
    app_env: str = Field(default="development")
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


settings = Settings()
