from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    document_id: str | None = Field(
        default=None,
        description="Optional caller-supplied document ID. Auto-generated if omitted.",
    )
    text: str = Field(..., min_length=1, description="Raw text content to ingest")
    source: str = Field(default="", description="Source label (e.g. 'docs', 'kb', 'url')")
    metadata: dict = Field(default_factory=dict)


class IngestResponse(BaseModel):
    status: str
    document_id: str
    chunks_created: int
    collection_name: str
    job_id: str | None = None
