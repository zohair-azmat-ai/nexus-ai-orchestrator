# Nexus AI — Backend

FastAPI backend for the Nexus AI Multi-Agent RAG Orchestration Platform.

## Structure

```
app/
├── api/v1/          # Route handlers (health, chat, ingest, memory, observability)
├── core/            # Config, logger, correlation IDs, telemetry
├── db/              # PostgreSQL and Qdrant connection helpers
├── schemas/         # Pydantic request/response models
├── services/
│   ├── orchestrator/ # Staged pipeline engine
│   ├── memory/       # Conversation memory manager
│   ├── retrieval/    # RAG pipeline (ingest, chunk, embed, search)
│   ├── agents/       # Multi-agent layer
│   ├── llm/          # OpenAI client + prompt templates
│   └── events/       # Event logging
└── workers/         # Background job workers
```

## Quick Start

```bash
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## API Docs

Visit `http://localhost:8000/docs` for the interactive Swagger UI.

## Tests

```bash
pytest tests/ -v
```
