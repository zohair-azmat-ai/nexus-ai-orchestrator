<p align="center">
  <img src="docs/assets/nexus-ai-logo.png" alt="Nexus AI Logo" width="170" />
</p>

<h1 align="center">Nexus AI</h1>

<p align="center">
  <strong>Multi-Agent RAG Orchestration Platform</strong>
</p>

<p align="center">
  Nexus AI is a production-style AI platform for memory-aware conversations, grounded retrieval, multi-step planning, observability, async jobs, and human-in-the-loop escalation.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-active%20development-2563eb?style=for-the-badge" alt="Status badge" />
  <img src="https://img.shields.io/badge/phase-7.0%20Deployment-e11d48?style=for-the-badge" alt="Phase badge" />
  <img src="https://img.shields.io/badge/backend-FastAPI-0f766e?style=for-the-badge&logo=fastapi&logoColor=white" alt="Backend badge" />
  <img src="https://img.shields.io/badge/frontend-Next.js-111827?style=for-the-badge&logo=nextdotjs&logoColor=white" alt="Frontend badge" />
  <img src="https://img.shields.io/badge/tests-160%20passing-15803d?style=for-the-badge" alt="Tests badge" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-API%20layer-0ea5e9?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI badge" />
  <img src="https://img.shields.io/badge/Next.js-client%20app-7c3aed?style=flat-square&logo=nextdotjs&logoColor=white" alt="Next.js badge" />
  <img src="https://img.shields.io/badge/PostgreSQL-state%20store-16a34a?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL badge" />
  <img src="https://img.shields.io/badge/Qdrant-vector%20search-f59e0b?style=flat-square" alt="Qdrant badge" />
  <img src="https://img.shields.io/badge/OpenAI-LLM%20router-ef4444?style=flat-square&logo=openai&logoColor=white" alt="OpenAI badge" />
</p>

## Overview

Nexus AI is an advanced AI orchestration platform, not a simple chatbot wrapper. The repository combines a staged FastAPI orchestrator, memory and retrieval systems, specialized agents, tool-assisted execution, background jobs, observability, and an emerging human review workflow into a single backend-first operating layer for serious AI applications.

The project exists to answer a harder question than "how do we chat with an LLM?" It asks how to build an AI system that can route intelligently, stay grounded, remember the right things, expose traceable execution, recover safely when confidence is weak, and hand off to humans when risk is high.

## Why This Project Exists

- Most AI demos stop at prompt wiring. Nexus AI is built around orchestration, persistence, auditability, and extensibility.
- Real-world AI systems need memory freshness, retrieval quality control, tool-aware planning, async work, and production observability.
- Escalation and review matter. Nexus AI is moving toward a full human-in-the-loop operating model rather than pretending every answer should be fully autonomous.

## Current Capabilities

- Multi-stage orchestration pipeline with intake, memory, retrieval, triage, planning, response, escalation, and event logging.
- Specialized agents for support, research, summarization, planning, and escalation.
- Multi-step execution plans with deterministic chaining, tool recommendations, dependency tracking, and skip logic.
- Retrieval quality assessment with compacted context, strong/weak/none grounding signals, and memory-aware retrieval skipping.
- Memory freshness heuristics with summary reuse, recent-turn prioritization, and refresh recommendation signals.
- Async job system for ingestion, analytics, and memory summary workflows.
- Internal observability with traces, stage timings, metrics, and event enrichment.
- Human-in-the-loop escalation workflow with persistent cases, notes, assignment, status changes, and audit events.
- Reviewer/admin authentication with protected reviewer APIs and a frontend login flow.
- Deterministic evaluation suites for retrieval quality, memory quality, agent selection, and regression stability.
- Production readiness improvements for environment validation, Docker deployment, CI, and readiness checks.

## Architecture Summary

Nexus AI is organized around a backend-first orchestration core. The API receives requests, the orchestrator decides how much context and execution is needed, agents and tools produce grounded output, background jobs handle longer-running work, observability captures the full trail, and escalated cases can move into a persistent human review workflow.

```mermaid
flowchart LR
    U[User / Frontend] --> API[FastAPI API Layer]
    API --> ORCH[Orchestrator Engine]

    ORCH --> MEM[Memory Layer]
    ORCH --> RET[Retrieval Layer]
    ORCH --> AGENTS[Agent Layer]
    ORCH --> OBS[Observability]
    ORCH --> HITL[HITL Escalation]

    MEM --> PG[(PostgreSQL)]
    RET --> QD[(Qdrant)]
    AGENTS --> TOOLS[Tool Registry]
    AGENTS --> LLM[OpenAI Router]
    TOOLS --> JOBS[Async Jobs]
    JOBS --> PG
    OBS --> PG
    HITL --> PG
    HITL --> REVIEW[Human Review Queue]

    TOOLS --> RET
    TOOLS --> MEM
    JOBS --> OBS
    AGENTS --> OBS
    RET --> OBS
    MEM --> OBS
    ORCH --> REVIEW

    classDef blue fill:#153a75,stroke:#60a5fa,color:#eaf2ff,stroke-width:2px;
    classDef purple fill:#4c1d95,stroke:#c084fc,color:#f5ecff,stroke-width:2px;
    classDef green fill:#14532d,stroke:#4ade80,color:#ecfff3,stroke-width:2px;
    classDef orange fill:#7c2d12,stroke:#fb923c,color:#fff4ea,stroke-width:2px;
    classDef red fill:#7f1d1d,stroke:#f87171,color:#fff0f0,stroke-width:2px;

    class U,API,LLM blue;
    class ORCH,AGENTS purple;
    class MEM,PG green;
    class RET,QD,TOOLS,JOBS orange;
    class OBS,HITL,REVIEW red;
```

## Key Features

- Deterministic planning: simple requests stay single-step while complex requests expand into explainable multi-step plans.
- Context discipline: retrieval and memory are filtered, compacted, and routed intentionally instead of dumping raw context everywhere.
- Grounded response behavior: confidence and answer posture adapt to retrieval quality and memory freshness.
- Production-style visibility: traces, metrics, enriched events, and stage timings are built into the execution path.
- HITL-ready operations: escalations now become persistent review cases rather than transient runtime signals.

## Backend Highlights

- FastAPI service with modular route groups and typed schemas.
- SQLAlchemy-backed persistence for conversations, summaries, events, jobs, and escalation workflow state.
- Orchestrator engine with isolated stages and shared execution context.
- Service modules for agents, memory, retrieval, tools, jobs, observability, analytics, and escalation management.
- Clean extension path for future dashboard, reviewer operations, and production deployment hardening.

## Observability Highlights

- `trace_id` and correlation flow through requests, jobs, agents, tools, and escalation paths.
- Enriched event model with stage, component, latency, status, and execution metadata.
- Trace and metrics endpoints for operational inspection without external observability dependencies.
- Planning, retrieval quality, memory freshness, grounding mode, jobs, and escalation events are all auditable.

## Planning, Tools, and Jobs

- Planner supports deterministic agent chaining and context-aware step creation.
- Tool planning can recommend or skip work based on retrieval quality and available memory.
- Async jobs support document ingestion, memory summarization, and analytics aggregation.
- Tool calls and job execution remain observable and testable without requiring live external services.

## Repository Structure

```text
nexus-ai/
|-- README.md
|-- docs/
|   |-- assets/
|   |-- architecture.md
|   |-- api-contracts.md
|   `-- dev-status.md
|-- backend/
|   |-- README.md
|   |-- app/
|   |   |-- api/v1/
|   |   |-- core/
|   |   |-- db/
|   |   |-- schemas/
|   |   `-- services/
|   `-- tests/
`-- frontend/
    |-- app/
    |-- components/
    `-- public/
```

## Testing

The backend test suite is designed to run without live OpenAI, Qdrant, or PostgreSQL dependencies. The current repository state includes:

- `160` backend tests passing.
- Coverage for orchestration, planning, retrieval quality, memory freshness, jobs, observability, tools, and escalation workflow.
- In-memory and mocked test paths that keep development fast and deterministic.

```bash
cd backend
pytest tests -q
```

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url> nexus-ai
cd nexus-ai
cp backend/.env.example backend/.env
```

### 2. Install backend dependencies

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Start infrastructure and backend

```bash
docker compose up -d
uvicorn app.main:app --reload --port 8000
```

In development, the backend bootstraps these accounts automatically:

- `reviewer@nexus.local` / `ReviewerPass123!`
- `admin@nexus.local` / `AdminPass123!`

### 4. Start the frontend

```bash
cd ../frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local` if your backend is not running on `http://localhost:8000`.
For containerized Next.js deployments, you can also set `INTERNAL_API_BASE_URL` so server-side requests use an internal backend hostname while browsers keep using the public API URL.

### 5. Verify the platform

```bash
curl http://localhost:8000/api/v1/health
```

### 6. Sign in to the reviewer dashboard

Open `http://localhost:3000/login` and sign in with one of the development accounts above.

### 7. Run the evaluation suite

```bash
cd backend
.venv\Scripts\python.exe -m app.evals.runner --suite all --save-report
```

Reports are saved under `backend/eval_reports/`.

### 8. Run with Docker

```bash
docker compose up --build
```

For a production-oriented override:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Backend-specific environment and runtime details live in [backend/README.md](backend/README.md).

## Roadmap and Current Status

- Completed through Phase 5 Step 3: retrieval and memory quality optimization.
- Completed through Phase 7: production deployment polish and readiness.
- Next maturity direction: broader HITL tooling, release automation, and continued hardening of orchestration and observability.

For the latest implementation snapshot, see [docs/dev-status.md](docs/dev-status.md). Deployment-specific setup and cloud guidance are in [docs/deployment.md](docs/deployment.md).

## Backend Documentation

The root README is the main GitHub showcase and project overview. The backend-only setup, environment variables, API group summary, and test commands are documented in [backend/README.md](backend/README.md).

## License

MIT
