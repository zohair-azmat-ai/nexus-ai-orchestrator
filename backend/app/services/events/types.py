"""
Event Types — canonical names for all platform events.

Using string constants (not Enum) so they can be serialized directly
into JSON logs and future event store records without extra conversion.
"""

# Chat lifecycle
EVENT_API_REQUEST_STARTED = "api.request.started"
EVENT_API_REQUEST_COMPLETED = "api.request.completed"
EVENT_API_REQUEST_FAILED = "api.request.failed"
EVENT_CHAT_RECEIVED = "chat.received"
EVENT_CHAT_COMPLETED = "chat.completed"
EVENT_CHAT_FAILED = "chat.failed"

# Orchestrator stages
EVENT_STAGE_STARTED = "stage.started"
EVENT_STAGE_COMPLETED = "stage.completed"
EVENT_STAGE_FAILED = "stage.failed"
EVENT_PLAN_CREATED = "plan.created"
EVENT_PLAN_STEP_STARTED = "plan.step.started"
EVENT_PLAN_STEP_COMPLETED = "plan.step.completed"
EVENT_PLAN_STEP_FAILED = "plan.step.failed"
EVENT_PLAN_STEP_SKIPPED = "plan.step.skipped"
EVENT_PLAN_TOOL_RECOMMENDED = "plan.tool.recommended"
EVENT_PLAN_CONTEXT_ROUTED = "plan.context.routed"
EVENT_STAGE_INTAKE = "orchestrator.intake"
EVENT_STAGE_MEMORY = "orchestrator.memory"
EVENT_STAGE_RETRIEVAL = "orchestrator.retrieval"
EVENT_STAGE_TRIAGE = "orchestrator.triage"
EVENT_STAGE_RESPONSE = "orchestrator.response"
EVENT_STAGE_ESCALATION = "orchestrator.escalation"
EVENT_STAGE_LOG = "orchestrator.event_log"

# Agent events
EVENT_AGENT_SELECTED = "agent.selected"
EVENT_AGENT_EXECUTED = "agent.executed"
EVENT_AGENT_RESPONDED = "agent.responded"
EVENT_AGENT_ESCALATED = "agent.escalated"

# Memory events
EVENT_MEMORY_LOADED = "memory.loaded"
EVENT_MEMORY_SAVED = "memory.saved"
EVENT_MEMORY_SUMMARIZED = "memory.summarized"
EVENT_MEMORY_FRESHNESS_ASSESSED = "memory.freshness.assessed"
EVENT_MEMORY_SUMMARY_REFRESH_RECOMMENDED = "memory.summary.refresh_recommended"

# Retrieval events
EVENT_RETRIEVAL_SEARCHED = "retrieval.searched"
EVENT_RETRIEVAL_QUALITY_ASSESSED = "retrieval.quality.assessed"
EVENT_RETRIEVAL_CONTEXT_COMPACTED = "retrieval.context.compacted"
EVENT_INGEST_STARTED = "ingest.started"
EVENT_INGEST_COMPLETED = "ingest.completed"

# Tool events
EVENT_TOOL_CALLED = "tool.called"
EVENT_TOOL_RESULT = "tool.result"
EVENT_TOOL_ERROR = "tool.error"

# Background job events
EVENT_JOB_CREATED = "job.created"
EVENT_JOB_STARTED = "job.started"
EVENT_JOB_COMPLETED = "job.completed"
EVENT_JOB_FAILED = "job.failed"

# System events
EVENT_STARTUP = "system.startup"
EVENT_SHUTDOWN = "system.shutdown"
EVENT_HEALTH_CHECKED = "system.health_checked"
EVENT_RESPONSE_GROUNDING_MODE = "response.grounding.mode"
