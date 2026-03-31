from pydantic import BaseModel, Field


class EscalationCaseResponse(BaseModel):
    case_id: str
    conversation_id: str
    trace_id: str | None = None
    user_id: str
    escalation_reason: str
    severity: str
    status: str
    assigned_to: str | None = None
    latest_agent: str | None = None
    latest_summary: str | None = None
    created_at: str
    updated_at: str


class EscalationNoteResponse(BaseModel):
    note_id: str
    case_id: str
    author: str
    note_type: str
    content: str
    created_at: str


class EscalationCaseListResponse(BaseModel):
    cases: list[EscalationCaseResponse]
    total: int


class EscalationNoteListResponse(BaseModel):
    notes: list[EscalationNoteResponse]
    total: int


class EscalationAssignRequest(BaseModel):
    assigned_to: str = Field(..., min_length=1, max_length=255)
    actor: str | None = Field(default=None, max_length=255)
    move_to_in_review: bool = True


class EscalationStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(open|in_review|approved|rejected|resolved)$")
    actor: str | None = Field(default=None, max_length=255)


class EscalationNoteCreateRequest(BaseModel):
    author: str = Field(..., min_length=1, max_length=255)
    note_type: str = Field(..., pattern="^(system|agent|human)$")
    content: str = Field(..., min_length=1, max_length=4000)


class EscalationTestCreateRequest(BaseModel):
    customer_ref: str = Field(..., min_length=1, max_length=255, description="Customer reference or user ID for the test case")
    message: str = Field(..., min_length=1, max_length=2000, description="The escalation reason / message that triggered review")
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    channel: str = Field(default="test", max_length=100, description="Optional channel label (e.g. chat, email, test)")
