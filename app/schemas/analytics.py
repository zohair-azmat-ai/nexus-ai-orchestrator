from pydantic import BaseModel


class AnalyticsSummaryResponse(BaseModel):
    total_tickets: int
    total_escalations: int
    escalation_rate: float
    avg_response_time_seconds: float
