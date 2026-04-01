# Nexus AI — API Contracts

Base URL: `http://localhost:8000/api/v1`

All responses include the `X-Correlation-ID` header.

---

## GET /health

Returns system health including dependency availability.

**Response 200**
```json
{
  "status": "ok",
  "service": "nexus-ai",
  "version": "0.1.0",
  "environment": "development",
  "postgres": true,
  "qdrant": true,
  "timestamp": "2026-03-30T12:00:00"
}
```

**Status values:** `ok` | `degraded`

---

## POST /chat

Submit a message for orchestrated processing.

**Request**
```json
{
  "user_id": "user-123",
  "session_id": "session-abc",
  "message": "What is the refund policy?",
  "history": [
    { "role": "user", "content": "Hello" },
    { "role": "assistant", "content": "Hi! How can I help?" }
  ],
  "metadata": {}
}
```

**Response 200**
```json
{
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "answer": "Our refund policy allows returns within 30 days...",
  "selected_agent": "support",
  "memory_used": true,
  "retrieval_used": false,
  "event_summary": {
    "stage_events": [...],
    "escalated": false,
    "duration_ms": 142.5
  }
}
```

**Selected agent values:** `support` | `research` | `summarizer` | `planner` | `escalation`

---

## POST /ingest

Ingest a document into the retrieval pipeline. *(Phase 1: stub)*

**Request**
```json
{
  "source": "docs",
  "content": "Full text of the document to ingest...",
  "metadata": { "category": "policy", "version": "2026" }
}
```

**Response 200**
```json
{
  "status": "ok",
  "document_id": "uuid-here",
  "chunks_created": 4
}
```

---

## GET /memory/{user_id}

Retrieve memory context for a user. *(Phase 1: in-process only)*

**Response 200**
```json
{
  "user_id": "user-123",
  "session_count": 2,
  "short_term": [
    { "role": "user", "content": "Hello", "timestamp": null },
    { "role": "assistant", "content": "Hi!", "timestamp": null }
  ],
  "long_term_summary": null,
  "metadata": {}
}
```

---

## GET /observability/health

Lightweight observability status and in-memory metrics.

**Response 200**
```json
{
  "status": "ok",
  "service": "nexus-ai",
  "version": "0.1.0",
  "environment": "development",
  "metrics": {
    "chat.received": 42,
    "agent.support": 30
  }
}
```
