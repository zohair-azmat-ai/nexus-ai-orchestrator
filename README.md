---
title: Nexus AI Orchestrator
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

<div align="center">
  <img src="docs/assets/nexus-ai-banner.png" width="1200" />
</div>

<h1 align="center">Nexus AI</h1>

<h3 align="center">Multi-Agent RAG Orchestration Platform</h3>

<p align="center">
  Production-grade AI system with memory, retrieval, planning, observability, public customer reporting, analytics, and human-in-the-loop workflows.
</p>

<br/>

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0f766e?style=flat-square&logo=fastapi&logoColor=white" />
  &nbsp;
  <img src="https://img.shields.io/badge/Next.js-111827?style=flat-square&logo=nextdotjs&logoColor=white" />
  &nbsp;
  <img src="https://img.shields.io/badge/PostgreSQL-16a34a?style=flat-square&logo=postgresql&logoColor=white" />
  &nbsp;
  <img src="https://img.shields.io/badge/Qdrant-f59e0b?style=flat-square&logoColor=white" />
  &nbsp;
  <img src="https://img.shields.io/badge/OpenAI-7c3aed?style=flat-square&logo=openai&logoColor=white" />
  &nbsp;
  <img src="https://img.shields.io/badge/Docker-2563eb?style=flat-square&logo=docker&logoColor=white" />
</p>

---

## Latest Capabilities

- Public customer issue intake at `GET /report`
- Premium analytics dashboard at `GET /analytics`
- Backend analytics summary at `GET /api/v1/analytics/summary`
- Auto-assignment of high-severity escalations to `reviewer_default`
- Notification stub for future email and WhatsApp delivery
- SaaS plan foundation with monthly ticket limits

## New SaaS Features

### Customer Report UI

The `/report` experience now supports public issue submission with a premium dark UI and direct integration into the existing chat-to-escalation pipeline.

- No auth token required
- Browser-generated `session_id`
- `user_id` derived from email or customer reference, with a guest fallback
- Priority-aware message construction for escalation compatibility
- Success state with escalation case details when a case is created

### Analytics Dashboard

The `/analytics` route surfaces live support metrics with animated presentation:

- Total tickets
- Total escalations
- Escalation rate
- Average response time

### Auto-Assignment and Notifications

When a new escalation is created with `severity == "high"`:

- `assigned_to` is automatically set to `reviewer_default`
- the case is moved into review
- a notification stub is logged for future delivery channels

### SaaS Plans and Usage Limits

Monthly usage enforcement now supports:

- `free`: 50 tickets
- `pro`: 500 tickets
- `team`: unlimited

If a customer exceeds their plan allowance, the API returns `429 Too Many Requests` with a clear upgrade-style response.

## System Status

| Component | Status |
|:---|:---|
| Backend API | ✅ Ready |
| Frontend UI | ✅ Ready |
| Customer Report Route | ✅ Enabled |
| Analytics Dashboard | ✅ Enabled |
| HITL Escalation Workflow | ✅ Enabled |
| Auto-Assignment | ✅ Enabled |
| Notification Stub | ✅ Enabled |
| SaaS Usage Enforcement | ✅ Enabled |

## Routes and APIs

- `GET /` - service info
- `GET /report` - public customer issue reporting page
- `GET /analytics` - premium analytics dashboard
- `POST /api/v1/chat` - orchestrated support intake and escalation entrypoint
- `GET /api/v1/analytics/summary` - support metrics summary
- `GET /api/v1/health` - health check
- `GET /api/v1/ready` - readiness check
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc reference

## Project Structure

```text
backend/
  app/              - FastAPI app, routes, services, orchestrator, agents, tools
  tests/            - Backend tests
  evals/            - Deterministic evaluation runner and benchmark cases

frontend/
  app/              - Next.js app router pages
  components/       - UI components including report and escalation flows
  lib/              - API client and utility modules

app/
  static/           - Hugging Face compatible premium public report and analytics pages
  api/              - FastAPI routes for static public entrypoints and APIs

docs/
specs/
prompt_history/
```

## Environment Variables

| Variable | Description |
|:---|:---|
| `OPENAI_API_KEY` | OpenAI API key for LLM inference |
| `DATABASE_URL` | PostgreSQL connection string |
| `QDRANT_URL` | Qdrant instance URL |
| `QDRANT_API_KEY` | Qdrant API key if required |
| `AUTH_SECRET_KEY` | JWT signing secret |
| `APP_ENV` | Set to `production` for deployment |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed origins |

## Development Notes

- Startup keeps the existing table bootstrap flow and performs a lightweight runtime schema sync for `users.plan`
- Existing escalation, auth, reviewer, and deployment flows remain intact
- The Hugging Face Space remains Docker-compatible

## Documentation

| Resource | Description |
|:---|:---|
| [backend/README.md](backend/README.md) | Backend setup and API usage |
| [docs/architecture.md](docs/architecture.md) | Architecture decisions |
| [docs/api-contracts.md](docs/api-contracts.md) | API contract reference |
| [docs/deployment.md](docs/deployment.md) | Deployment guidance |
| [docs/dev-status.md](docs/dev-status.md) | Current implementation snapshot |

## Source

[GitHub Repository](https://github.com/zohair-azmat-ai/nexus-ai-orchestrator)
