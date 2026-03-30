"""
Event Types — canonical names for all platform events.

Using string constants (not Enum) so they can be serialized directly
into JSON logs and future event store records without extra conversion.
"""

# Chat lifecycle
EVENT_CHAT_RECEIVED = "chat.received"
EVENT_CHAT_COMPLETED = "chat.completed"
EVENT_CHAT_FAILED = "chat.failed"

# Orchestrator stages
EVENT_STAGE_INTAKE = "orchestrator.intake"
EVENT_STAGE_MEMORY = "orchestrator.memory"
EVENT_STAGE_RETRIEVAL = "orchestrator.retrieval"
EVENT_STAGE_TRIAGE = "orchestrator.triage"
EVENT_STAGE_RESPONSE = "orchestrator.response"
EVENT_STAGE_ESCALATION = "orchestrator.escalation"
EVENT_STAGE_LOG = "orchestrator.event_log"

# Agent events
EVENT_AGENT_SELECTED = "agent.selected"
EVENT_AGENT_RESPONDED = "agent.responded"
EVENT_AGENT_ESCALATED = "agent.escalated"

# Memory events
EVENT_MEMORY_LOADED = "memory.loaded"
EVENT_MEMORY_SAVED = "memory.saved"
EVENT_MEMORY_SUMMARIZED = "memory.summarized"

# Retrieval events
EVENT_RETRIEVAL_SEARCHED = "retrieval.searched"
EVENT_INGEST_STARTED = "ingest.started"
EVENT_INGEST_COMPLETED = "ingest.completed"

# System events
EVENT_STARTUP = "system.startup"
EVENT_SHUTDOWN = "system.shutdown"
EVENT_HEALTH_CHECKED = "system.health_checked"
