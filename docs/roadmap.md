# Nexus AI — Development Roadmap

## Phase 1 — Foundation (Current)

**Goal:** Production-quality project scaffold with all architectural layers in place.

- [x] Repo structure and documentation
- [x] FastAPI backend with full route layer
- [x] Staged orchestrator pipeline engine
- [x] Correlation ID middleware
- [x] Structured JSON logging
- [x] PostgreSQL connection scaffold (SQLAlchemy async)
- [x] Qdrant connection scaffold
- [x] OpenAI client wrapper
- [x] Memory module scaffold
- [x] Retrieval module scaffold (ingest, chunk, embed, index, search)
- [x] Multi-agent scaffold (support, research, summarizer, planner, escalation)
- [x] Event logging types and emitter
- [x] Health endpoint + observability endpoint
- [x] Next.js frontend landing page
- [x] Docker Compose for infrastructure
- [x] Backend tests (health + chat)

---

## Phase 2 — Memory + RAG Integration

**Goal:** Replace all stubs with real data layer integration.

- [ ] PostgreSQL schema + Alembic migrations (conversations, messages, users)
- [ ] MemoryManager backed by real DB reads/writes
- [ ] Real Qdrant collection creation and upsert
- [ ] EmbeddingsService calling OpenAI API
- [ ] SemanticSearch performing real Qdrant queries
- [ ] Ingest endpoint fully functional end-to-end
- [ ] Memory endpoint reading from DB
- [ ] Integration tests for retrieval pipeline

---

## Phase 3 — Multi-Agent Execution

**Goal:** Agents perform real LLM calls with context-aware prompts.

- [ ] LLM-powered triage (intent classification with confidence)
- [ ] Support agent: real OpenAI call with retrieval context injection
- [ ] Research agent: multi-step retrieval + synthesis
- [ ] Summarizer agent: LLM-powered conversation summarization
- [ ] Planner agent: chain-of-thought planning prompts
- [ ] Escalation agent: webhook integration placeholder
- [ ] Prompt versioning and A/B testing scaffold
- [ ] Agent-level evaluation metrics

---

## Phase 4 — Async Workers + Analytics

**Goal:** Non-blocking background processing and real analytics.

- [ ] Task queue integration (ARQ or Celery)
- [ ] Embedding worker: async batch embedding jobs
- [ ] Memory worker: session compaction and summarization
- [ ] Analytics worker: event log aggregation
- [ ] PostgreSQL event_log table + persistence
- [ ] Analytics API endpoint with real metrics
- [ ] Background ingest pipeline

---

## Phase 5 — Observability + Production Hardening

**Goal:** Full production readiness with enterprise-grade observability.

- [ ] OpenTelemetry instrumentation (traces + spans)
- [ ] Prometheus metrics exporter
- [ ] Grafana dashboard templates
- [ ] Rate limiting middleware
- [ ] Authentication (JWT / API key)
- [ ] Request validation hardening
- [ ] Error classification and retry policies
- [ ] Load testing + performance baselines
- [ ] Full CI/CD pipeline (GitHub Actions)
- [ ] Docker production build + Kubernetes manifests

---

## Phase 6+ — Distributed Architecture

**Goal:** Extract services for independent scaling.

- [ ] Memory service → independent microservice
- [ ] Retrieval service → independent microservice
- [ ] Agent runner → independent pool with message queue
- [ ] Event store → dedicated streaming pipeline (Kafka/Kinesis)
- [ ] Multi-tenant support
- [ ] Custom LLM support (Ollama, Azure OpenAI)
