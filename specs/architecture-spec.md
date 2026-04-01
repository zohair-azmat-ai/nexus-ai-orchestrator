# Nexus AI — Architecture Specification

## Approach: Modular Monolith

Nexus AI starts as a modular monolith — one deployable unit with clearly separated internal modules. Each service boundary is defined by module interfaces, not network calls. This means:

- **Fast development:** no network latency between services in early phases
- **Clear boundaries:** services are importable but not entangled
- **Easy extraction:** each module can be broken out into a microservice in Phase 6 without rewriting business logic

---

## Service Boundaries

| Module | Owns | Depends On |
|---|---|---|
| Orchestrator | Pipeline stages, routing policies | Memory, Retrieval, Agents |
| Memory | Conversation history, summaries | PostgreSQL |
| Retrieval | Ingest, chunking, embeddings, search | Qdrant, OpenAI Embeddings |
| Agents | Agent logic, prompt building | LLM Client, Retrieval |
| LLM | OpenAI client, prompt templates, router | OpenAI API |
| Events | Event emission, event types | Logger |
| Analytics | Metrics aggregation | Events |

---

## Data Flow

```
Request
  ↓
[Intake]  — validate, enrich
  ↓
[Memory]  — load history from Postgres
  ↓
[Retrieval] — embed query, search Qdrant
  ↓
[Triage]  — select agent based on intent
  ↓
[Response] — agent builds prompt, calls OpenAI
  ↓
[Escalation] — check escalation policy
  ↓
[Event Log] — emit structured event
  ↓
Response
```

---

## Configuration Strategy

All configuration flows through `app/core/config.py` using `pydantic-settings`. Environment variables are the single source of truth. No hardcoded credentials anywhere in the codebase.

---

## Async Strategy

- All FastAPI route handlers are `async def`
- All service methods are `async def`
- Database operations use SQLAlchemy async engine
- Qdrant operations use `AsyncQdrantClient`
- OpenAI calls use `AsyncOpenAI`
- Background work uses `asyncio` workers (Phase 4: task queue)

---

## Error Handling Strategy

- Service methods raise exceptions with clear messages
- Route handlers catch exceptions and return typed error responses
- Orchestrator stages have per-stage error isolation
- All errors are logged with correlation ID

---

## Future Scale Path

**Phase 2:** Replace in-memory stubs with real DB + Qdrant
**Phase 3:** Replace stage stubs with real LLM calls
**Phase 4:** Move workers to ARQ/Celery; add task queue
**Phase 5:** Add OTEL tracing, Prometheus metrics
**Phase 6:** Split into independent services with message passing
