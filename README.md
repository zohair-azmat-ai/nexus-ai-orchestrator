---
title: Nexus AI Orchestrator
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Nexus AI - Multi-Agent RAG Orchestration Platform

Production-grade AI backend with memory, retrieval, multi-agent planning, observability, public customer intake, reviewer escalations, and SaaS-ready usage controls.

## Latest Capabilities

- Public issue submission at `GET /report` with premium dark UI and live integration into `POST /api/v1/chat`
- Premium analytics dashboard at `GET /analytics` backed by `GET /api/v1/analytics/summary`
- Deterministic auto-assignment of high-severity escalations to `reviewer_default`
- Notification stub with email and WhatsApp-ready metadata logging
- SaaS plan foundation with monthly ticket limits for `free`, `pro`, and `team`

## Routes and APIs

- `GET /` - service info
- `GET /report` - public customer issue reporting page
- `GET /analytics` - premium analytics dashboard
- `GET /api/v1/health` - health check
- `GET /api/v1/ready` - readiness check
- `POST /api/v1/chat` - orchestrated support intake and escalation entrypoint
- `GET /api/v1/analytics/summary` - total tickets, total escalations, escalation rate, and average response time
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc reference

## Customer Report UI

The `/report` route is a public intake page for customer issues.

- No auth token is sent
- `session_id` is generated in the browser
- `user_id` is derived from the provided email or customer reference, or falls back to a generated guest identifier
- Message construction appends urgency context so the current escalation pipeline remains fully compatible
- Successful submissions show review confirmation and escalation details when a case is created

## Analytics Dashboard

The `/analytics` route renders a premium dark dashboard with animated stats:

- Total tickets
- Total escalations
- Escalation rate
- Average response time

The backend endpoint is:

- `GET /api/v1/analytics/summary`

## Auto-Assignment and Notifications

When the escalation workflow creates a high-severity case, Nexus AI now:

- auto-assigns the case to `reviewer_default`
- moves the case into review
- creates a notification log entry through a stub notifier service

The notification structure is prepared for future delivery channels:

- email
- WhatsApp

## SaaS Plans and Usage Limits

User accounts now include a `plan` field and monthly usage is tracked in the database.

- `free`: 50 tickets per month
- `pro`: 500 tickets per month
- `team`: unlimited

If a customer exceeds their monthly allowance, `POST /api/v1/chat` returns a clear `429` response so billing can be connected later without reworking the intake pipeline.

## Project Structure

Key additions in this upgrade:

- `app/api/public.py` - public page routes for `/report` and `/analytics`
- `app/api/v1/analytics.py` - analytics summary API
- `app/services/saas/` - plan resolution, limit enforcement, and usage tracking
- `app/services/notifications/` - stub notification service
- `app/static/` - premium static UI assets
- `app/db/models/ticket_usage.py` - monthly ticket usage persistence
- `app/db/models/notification.py` - notification audit records

## Environment Variables

Set the following secrets in the Space settings:

| Variable | Description |
|:---|:---|
| `OPENAI_API_KEY` | OpenAI API key for LLM inference |
| `DATABASE_URL` | PostgreSQL connection string |
| `QDRANT_URL` | Qdrant instance URL |
| `QDRANT_API_KEY` | Qdrant API key if required |
| `AUTH_SECRET_KEY` | JWT signing secret |
| `APP_ENV` | Set to `production` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed origins |

## Development Notes

- Startup keeps the current table bootstrap flow and now performs a lightweight runtime schema sync for the new `users.plan` column.
- Existing auth, escalation, analytics, reviewer, and deployment flows stay intact.
- The app remains Hugging Face Spaces Docker compatible.

## Source

[GitHub Repository](https://github.com/zohair-azmat-ai/nexus-ai-orchestrator)
