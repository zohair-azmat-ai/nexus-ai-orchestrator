# Nexus AI — Project Prompt History

This document records the architectural decisions, planning prompts, and build directives that shaped the Nexus AI project. It serves as a transparent record of the project's planning maturity for future contributors and reviewers.

---

## Entry 1 — Project Kickoff

**Date:** 2026-03-30
**Type:** Project Definition

### Summary

Nexus AI was defined as a brand-new multi-agent RAG orchestration platform, explicitly separate from any prior AI projects (e.g. SupportPilot AI). The founding directive emphasized that this should **not** feel like a basic chatbot — it should feel like a real AI operating platform with production-style architecture.

### Key decisions made:
- Project name: **Nexus AI**
- Direction: Level 6 → Level 7 AI architecture
- Philosophy: production-style from day one, not a toy repo
- No LangGraph in Phase 1 — custom orchestrator first
- Modular monolith architecture with clear service boundaries
- Async-first FastAPI backend
- Clean separation: Interface → Orchestrator → Memory → Retrieval → Agents → Observability

---

## Entry 2 — Architecture Prompt

**Date:** 2026-03-30
**Type:** Architecture Specification

### Summary

The high-level architecture was defined as a staged pipeline orchestrator:

```
Client → API Intake → Orchestrator → Memory + Retrieval + Agents → Response → Event Logging
```

Six core layers were defined:
1. **Interface Layer** — Next.js + FastAPI routes
2. **Orchestrator Layer** — 7-stage pipeline engine
3. **Memory Layer** — short-term, long-term, summaries, rules
4. **Retrieval Layer** — ingest, chunk, embed, index, search
5. **Multi-Agent Layer** — support, research, summarizer, planner, escalation
6. **Infrastructure Layer** — correlation IDs, structured logs, metrics, events

### Key architectural decisions:
- Correlation IDs generated or propagated per request via middleware
- Structured JSON logging using `python-json-logger` with context injection
- Pydantic `BaseSettings` for all configuration (no hardcoded values)
- SQLAlchemy async engine for PostgreSQL
- `AsyncQdrantClient` for vector operations
- `AsyncOpenAI` for all LLM calls
- In-process memory for Phase 1, DB-backed for Phase 2

---

## Entry 3 — Phase 1 Build Prompt

**Date:** 2026-03-30
**Type:** Full Build Directive

### Summary

A comprehensive build prompt was provided specifying the exact repo structure, all required files, and implementation rules. The quality bar set was: **"The result must look like a serious advanced AI system starter repo, not a toy repo."**

### Scope of Phase 1 build:
- 60+ files across backend, frontend, docs, specs, and root
- FastAPI backend with 5 route groups and 7-stage orchestrator
- Multi-agent layer with base class and 5 specialized agents
- Full retrieval pipeline scaffold (5 modules)
- Memory layer scaffold (3 modules)
- LLM layer (client wrapper, prompts, router)
- Event system (types + logger)
- Next.js frontend with Navbar, Hero, FeatureGrid
- Docker Compose for Postgres + Qdrant
- Comprehensive docs and specs

### Tech stack confirmed:
- Backend: FastAPI (Python 3.11+)
- Frontend: Next.js 14 + Tailwind CSS
- Database: PostgreSQL (SQLAlchemy async)
- Vector DB: Qdrant
- AI: OpenAI (gpt-4o + text-embedding-3-small)
- Orchestration: Custom staged pipeline (no LangGraph in Phase 1)
- Logging: python-json-logger
- Testing: pytest + pytest-asyncio

---

## Notes for Future Claude Code Sessions

When continuing this project, note:

1. **Phase 2 starts with DB integration.** The next step is Alembic migrations and real PostgreSQL reads/writes in `MemoryManager`.

2. **All stubs are clearly marked.** Every stub in the codebase has a comment like `# Phase 2: replace with real X` — search for these to find integration points.

3. **The orchestrator is stage-based, not LangGraph.** Do not introduce LangGraph unless the user explicitly requests it and Phase 3 work begins.

4. **Event types are centralized.** Add new event types to `app/services/events/types.py`, never inline strings.

5. **Config is always via settings.** Never hardcode URLs, keys, or environment-specific values. Always read from `app.core.config.settings`.

6. **All service modules have singleton instances.** E.g. `memory_manager`, `ingest_service`, `semantic_search` — use these, don't instantiate new ones in routes.

7. **Tests are async.** Use `pytest-asyncio` and `ASGITransport` pattern already established in `tests/`.
