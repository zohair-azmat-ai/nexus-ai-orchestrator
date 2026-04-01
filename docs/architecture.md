# Nexus AI — Architecture

## Overview

Nexus AI uses a **modular monolith** architecture. All services live within a single deployable unit (the FastAPI backend), but are organized into clearly separated modules with defined boundaries. This approach optimizes for development velocity in early phases while preserving the ability to extract services (memory, retrieval, agents) into independent microservices in later phases.

---

## Layered Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Interface Layer                     │
│         Next.js Frontend  │  FastAPI Routes           │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│               Orchestrator Layer                      │
│  intake → memory → retrieval → triage → response     │
│          → escalation → event log                     │
└──────┬──────────┬──────────┬──────────────────────────┘
       │          │          │
┌──────▼──┐  ┌───▼────┐  ┌──▼──────────────────────────┐
│ Memory  │  │  RAG   │  │       Agent Layer            │
│ Layer   │  │ Layer  │  │  support / research /        │
│         │  │        │  │  summarizer / planner /      │
│Postgres │  │Qdrant  │  │  escalation                  │
└─────────┘  └────────┘  └──────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│           Infrastructure / Observability              │
│    Correlation IDs │ Structured Logs │ Events         │
│    Metrics-ready   │ Tracing-ready   │ Workers        │
└──────────────────────────────────────────────────────┘
```

---

## Request Lifecycle

1. **Client** sends POST `/api/v1/chat` with user message
2. **Correlation ID Middleware** generates or propagates `X-Correlation-ID`
3. **Chat Route** validates request via Pydantic schema
4. **Orchestrator Engine** executes the staged pipeline:

   | Stage | Responsibility |
   |---|---|
   | Intake | Normalize and enrich request |
   | Memory | Load conversation history |
   | Retrieval | Semantic search in Qdrant |
   | Triage | Select appropriate agent |
   | Response | Generate answer via agent + LLM |
   | Escalation | Apply escalation rules |
   | Event Log | Persist structured event record |

5. **Response** returned to client with correlation ID, answer, and event summary

---

## Orchestrator Stages (Detail)

### Intake Stage
- Parse user ID, session ID, message
- Enrich with request metadata
- Validate message constraints

### Memory Stage
- Load recent conversation turns (short-term)
- Load session summary if available (long-term)
- Apply memory rules (max turns, trim policy)

### Retrieval Stage
- Embed the user query
- Query Qdrant for top-K relevant chunks
- Format retrieved context for prompt injection

### Triage Stage
- Phase 1: keyword-based agent selection
- Phase 3: LLM-based intent classification with confidence scoring
- Available agents: support, research, summarizer, planner, escalation

### Response Stage
- Build agent-specific prompt (with history + retrieval context)
- Call OpenAI via LLM router
- Apply response formatting rules

### Escalation Stage
- Check escalation policy thresholds
- Mark request as escalated if triggered
- Phase 4: trigger real escalation workflow (webhook, ticket system)

### Event Log Stage
- Emit structured event record with all stage metadata
- Phase 4: persist to PostgreSQL event_log table

---

## Future Scaling Path

| Phase | Architecture Change |
|---|---|
| Phase 2 | Real PostgreSQL + Qdrant integration (remove stubs) |
| Phase 3 | LLM-powered triage + real agent execution |
| Phase 4 | Background workers via ARQ/Celery; async event persistence |
| Phase 5 | OpenTelemetry integration; Prometheus metrics; distributed tracing |
| Phase 6+ | Extract memory/retrieval/agents into independent services |
