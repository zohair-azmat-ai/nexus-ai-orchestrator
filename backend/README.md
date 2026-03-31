# Nexus AI Backend

This directory contains the FastAPI backend for Nexus AI. It is the execution core for orchestration, memory, retrieval, agents, tools, jobs, observability, and escalation workflow.

> The root [README.md](../README.md) is the main project overview. This file is intentionally backend-specific.

## Backend Purpose

The backend is responsible for:

- serving the API used by the frontend and external clients
- running the staged orchestration pipeline
- storing conversations, summaries, events, jobs, and escalation cases
- integrating retrieval with Qdrant and state with PostgreSQL
- exposing traces, metrics, and review-oriented operational endpoints

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL
- Qdrant
- Optional: Docker / Docker Compose for local infrastructure

### Environment Setup

```bash
cd backend
cp .env.example .env
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Key Environment Variables

These are the main backend settings used during development:

- `DATABASE_URL`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `QDRANT_COLLECTION_NAME`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `RAG_TOP_K`
- `RAG_MIN_SCORE`
- `MEMORY_SUMMARY_TRIGGER_COUNT`
- `MEMORY_RECENT_MESSAGE_LIMIT`
- `JOBS_INLINE_MODE`
- `ENABLE_ASYNC_MEMORY_SUMMARY`
- `ENABLE_ASYNC_INGEST`
- `LOG_LEVEL`

See [`.env.example`](./.env.example) for the full backend configuration surface.

## Run the Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Interactive API docs:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Run Tests

```bash
cd backend
pytest tests -q
```

The test suite uses isolated in-memory test infrastructure and mocks external services where needed.

## Run Evaluations

```bash
cd backend
.venv\Scripts\python.exe -m app.evals.runner --suite all --save-report
```

Available suites:

- `retrieval`
- `memory`
- `agent`
- `regression`
- `all`

Saved reports are written to `backend/eval_reports/` by default.

## Key API Groups

- `/api/v1/health`
  Health and service checks
- `/api/v1/chat`
  Main orchestrated chat execution
- `/api/v1/ingest`
  Document ingestion and retrieval pipeline entry points
- `/api/v1/memory`
  Memory and conversation summary access
- `/api/v1/jobs`
  Background job submission and inspection
- `/api/v1/observability`
  Trace and metrics endpoints
- `/api/v1/escalations`
  HITL escalation review workflow

## Backend Notes

- The backend is modular by design and organized around `api`, `schemas`, `db`, and `services`.
- The orchestrator is the central runtime path; agents, tools, jobs, and escalation workflow build on top of it.
- Keep project-level positioning, roadmap, and architecture storytelling in the root [README.md](../README.md).
