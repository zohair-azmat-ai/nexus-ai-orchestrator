from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    source: str = Field(..., description="Source identifier (e.g. 'docs', 'kb', 'url')")
    content: str = Field(..., description="Raw text content to ingest")
    metadata: dict = Field(default_factory=dict)


class IngestResponse(BaseModel):
    status: str
    document_id: str
    chunks_created: int
