---
title: Nexus AI Orchestrator
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Nexus AI — Multi-Agent RAG Orchestration Platform

Production-grade AI backend with memory, retrieval, multi-agent planning, observability, and human-in-the-loop workflows.

## API

Once running, the API is available at:

- `GET /` — service info
- `GET /api/v1/health` — health check
- `GET /api/v1/ready` — readiness check
- `GET /docs` — interactive Swagger UI
- `GET /redoc` — ReDoc reference

## Environment Variables

Set the following secrets in the Space settings:

| Variable | Description |
|:---|:---|
| `OPENAI_API_KEY` | OpenAI API key for LLM inference |
| `DATABASE_URL` | PostgreSQL connection string |
| `QDRANT_URL` | Qdrant instance URL |
| `QDRANT_API_KEY` | Qdrant API key (if required) |
| `AUTH_SECRET_KEY` | JWT signing secret |
| `APP_ENV` | Set to `production` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed origins |

## Source

[GitHub Repository](https://github.com/zohair-azmat-ai/nexus-ai-orchestrator)
