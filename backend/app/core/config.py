from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


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

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")


settings = Settings()
