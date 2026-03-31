# Nexus AI Deployment Guide

## Overview

Nexus AI deploys as two application services plus supporting infrastructure:

- `backend`: FastAPI orchestration API
- `frontend`: Next.js reviewer and product UI
- `postgres`: relational state store
- `qdrant`: vector database

For local development you can run the backend and frontend directly. For containerized environments, use Docker Compose as the default deployment path.

## Environment Variables

### Backend

These variables are the main production requirements:

- `APP_ENV=production`
- `DATABASE_URL`
- `QDRANT_URL`
- `OPENAI_API_KEY`
- `AUTH_SECRET_KEY`
- `CORS_ALLOWED_ORIGINS`

Optional but commonly set:

- `QDRANT_API_KEY`
- `QDRANT_COLLECTION_NAME`
- `OPENAI_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `LOG_LEVEL`

Use [backend/.env.example](C:/Users/Zohair/Desktop/Zohair/nexus-ai/backend/.env.example) as the template.

### Frontend

Required:

- `NEXT_PUBLIC_API_BASE_URL`

Optional compatibility fallback:

- `NEXT_PUBLIC_API_URL`
- `INTERNAL_API_BASE_URL` for server-side requests from a containerized Next.js runtime

Use [frontend/.env.local.example](C:/Users/Zohair/Desktop/Zohair/nexus-ai/frontend/.env.local.example) as the template.

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

## Docker Deployment

### Start the full stack

```bash
docker compose up --build
```

### Production-oriented override

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

### Validate the compose configuration

```bash
docker compose config
```

## Health Checks

Backend endpoints:

- `/api/v1/health`: liveness
- `/api/v1/ready`: readiness with dependency checks

Readiness verifies:

- database connectivity
- Qdrant connectivity

## Tests and Evals

### Backend tests

```bash
cd backend
pytest tests -q
```

### Evaluation suite

```bash
cd backend
.venv\Scripts\python.exe -m app.evals.runner --suite all --save-report
```

### Frontend checks

```bash
cd frontend
npm run lint
npm run build
```

## Example Production Flow

1. Provision PostgreSQL and Qdrant.
2. Set backend production environment variables.
3. Build and deploy the backend container.
4. Set `NEXT_PUBLIC_API_BASE_URL` for the frontend deployment.
5. Build and deploy the frontend.
6. Verify `/api/v1/health` and `/api/v1/ready`.
7. Run the eval suite after release candidates when appropriate.

## Vercel Frontend Deployment

1. Import the `frontend` directory as the Vercel project root.
2. Set `NEXT_PUBLIC_API_BASE_URL` to the public backend URL.
3. Use the default Next.js build command:
   - `npm run build`
4. Use the default start command for Vercel-hosted Next.js.

## Hugging Face Spaces or Docker Backend Deployment

### Docker-based deployment

1. Build the backend image from [backend/Dockerfile](C:/Users/Zohair/Desktop/Zohair/nexus-ai/backend/Dockerfile).
2. Supply production values for `DATABASE_URL`, `QDRANT_URL`, `OPENAI_API_KEY`, and `AUTH_SECRET_KEY`.
3. Run:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Hugging Face Spaces

If deploying the backend in a Docker Space:

1. Point the Space at the backend container setup.
2. Add the backend environment variables in the Space settings.
3. Expose port `8000`.
4. Confirm the public Space URL is used as `NEXT_PUBLIC_API_BASE_URL` in the frontend deployment.
