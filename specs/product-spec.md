# Nexus AI — Product Specification

## What is Nexus AI?

Nexus AI is a multi-agent RAG orchestration platform. It provides an intelligent processing layer that sits between user queries and AI responses, routing each request through a structured pipeline of memory, retrieval, and specialized agents.

It is designed to feel like an **AI operating platform** — not a chatbot wrapper. The system maintains context across sessions, retrieves grounding knowledge from a vector store, and dispatches to the most appropriate agent for each type of request.

---

## Target Direction

- **Level 6–7 AI architecture:** persistent memory, semantic retrieval, multi-agent coordination, event logging, observability
- **Production-style from day one:** correlation IDs, structured logging, event store, typed schemas, async patterns
- **Phase-based growth:** scaffold first, integrate second, optimize third — no premature optimization

---

## Core Capabilities (Full Vision)

| Capability | Description |
|---|---|
| Memory | Short and long-term per-user conversation history |
| Retrieval | Semantic search over ingested knowledge base |
| Multi-agent routing | Intent-aware dispatch to specialized agents |
| Orchestration | Staged pipeline with policy-controlled flow |
| Observability | Correlation IDs, events, metrics, tracing |
| Analytics | Usage patterns, agent performance, latency |

---

## Non-Goals

- **Not a general-purpose LLM API wrapper.** Nexus AI is an orchestration platform, not a thin OpenAI proxy.
- **Not a conversational UI product.** The frontend is an operator dashboard, not an end-user chat app.
- **Not LangChain-dependent.** The orchestration engine is custom-built for full control and observability.
- **Not a SaaS product in Phase 1.** Multi-tenancy, billing, and user auth are out of scope until Phase 5.
- **Not SupportPilot AI.** This is a completely separate system with different architecture, branding, and goals.

---

## Success Criteria

Phase 1 complete when:
- [ ] All endpoints respond correctly to test requests
- [ ] Orchestrator pipeline logs stages for every request
- [ ] Correlation ID present in all logs and responses
- [ ] Docker Compose starts Postgres + Qdrant cleanly
- [ ] Frontend landing page loads without errors
- [ ] All tests pass
