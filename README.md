# Nexus AI

<p align="center">
  <img src="docs/assets/nexus-ai-logo.png" alt="Nexus AI Logo" width="180" />
</p>

<p align="center">
  <strong>Multi-Agent RAG Orchestration Platform</strong><br/>
  Production-grade AI operating infrastructure built for scale
</p>

---

## Overview

**Nexus AI** is a production-style multi-agent RAG (Retrieval-Augmented Generation) orchestration platform. It is designed to act as an intelligent AI operating layer — routing queries through memory, retrieval, and specialized agents to produce accurate, context-aware responses.

This is **not** a basic chatbot. It is an AI infrastructure project targeting Level 6–7 architecture: persistent memory, semantic retrieval, multi-agent coordination, event logging, and observability built in from day one.

> This project is entirely separate from SupportPilot AI. It is a new system with fresh architecture, branding, and goals.

---

## Architecture Summary

```
Client
  │
  ▼
FastAPI (API Intake)
  │
  ▼
Orchestrator Engine
  ├── Intake Stage
  ├── Memory Stage        ← PostgreSQL conversation history
  ├── Retrieval Stage     ← Qdrant vector search
  ├── Triage Stage        ← Agent selection
  ├── Response Stage      ← LLM call via OpenAI
  ├── Escalation Stage
  └── Event Logging Stage ← Structured logs + event store
         │
         ▼
    Structured Response
```

### Core Layers

| Layer | Description |
|---|---|
| Interface | Next.js frontend + FastAPI routes |
| Orchestrator | Staged pipeline engine with policy control |
| Memory | Short-term and long-term conversation memory |
| Retrieval | Document ingestion, chunking, embedding, vector search |
| Agents | Support, Research, Summarizer, Planner, Escalation |
| Infrastructure | Correlation IDs, structured logging, event store, metrics-ready |

---

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | Next.js 14 (App Router) + Tailwind CSS |
| Backend | FastAPI (Python 3.11+) |
| Database | PostgreSQL (via SQLAlchemy) |
| Vector DB | Qdrant |
| AI / LLM | OpenAI (GPT-4o) |
| Orchestration | Custom staged pipeline engine |
| Logging | python-json-logger + structured format |
| Containerization | Docker Compose |

---

## Repository Structure

```
nexus-ai/
├── frontend/                   # Next.js frontend
│   ├── app/                    # App router pages
│   ├── components/             # UI components
│   ├── lib/                    # Utilities
│   ├── hooks/                  # React hooks
│   └── public/logo/            # Logo assets
│
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/v1/             # Route handlers
│   │   ├── core/               # Config, logger, IDs, telemetry
│   │   ├── db/                 # PostgreSQL + Qdrant clients
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   │   ├── orchestrator/   # Staged pipeline engine
│   │   │   ├── memory/         # Memory management
│   │   │   ├── retrieval/      # RAG pipeline
│   │   │   ├── agents/         # Multi-agent layer
│   │   │   ├── llm/            # OpenAI client + prompts
│   │   │   └── events/         # Event logging
│   │   └── workers/            # Background task workers
│   └── tests/
│
├── docs/                       # Architecture + API docs
├── specs/                      # Product + technical specs
├── prompt_history/             # Project planning history
├── docker-compose.yml
└── README.md
```

---

## Phase Roadmap

| Phase | Focus | Status |
|---|---|---|
| Phase 1 | Foundation: API, orchestrator skeleton, scaffolds | ✅ In Progress |
| Phase 2 | Memory + RAG: real PostgreSQL + Qdrant integration | Planned |
| Phase 3 | Multi-Agent Execution: live agent routing + LLM calls | Planned |
| Phase 4 | Async Workers + Analytics | Planned |
| Phase 5 | Observability + Production Hardening | Planned |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose

### 1. Clone and configure

```bash
git clone <repo-url> nexus-ai
cd nexus-ai

# Backend env
cp backend/.env.example backend/.env

# Frontend env
cp frontend/.env.local.example frontend/.env.local
```

### 2. Start infrastructure

```bash
docker-compose up -d
```

### 3. Start backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Start frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. Verify

```bash
curl http://localhost:8000/api/v1/health
```

---

## Why Nexus AI?

Most RAG systems are wrappers. Nexus AI is built as an **operating platform**: it separates concerns cleanly (memory, retrieval, agents, orchestration), uses production patterns (correlation IDs, structured logs, event store), and is designed to grow from Phase 1 scaffolding to a fully autonomous multi-agent system.

---

## License

MIT
