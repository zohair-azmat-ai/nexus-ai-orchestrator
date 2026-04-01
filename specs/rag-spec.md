# Nexus AI — RAG Specification

## Pipeline Overview

```
Raw Document
     ↓
[Ingest Service]  — receive content + metadata
     ↓
[Text Chunker]    — split into overlapping chunks
     ↓
[Embeddings]      — generate dense vectors via OpenAI
     ↓
[Qdrant Indexer]  — upsert vectors + metadata into collection
     ↓
    (stored)

Query Time:
     ↓
[Embed Query]     — generate query vector
     ↓
[Semantic Search] — Qdrant nearest-neighbor search
     ↓
[Format Context]  — concatenate top-K chunks for prompt
     ↓
[Agent Prompt]    — inject context into LLM prompt
```

---

## Ingestion

| Field | Value |
|---|---|
| Input | Raw text content + source identifier + metadata |
| Entry point | `POST /api/v1/ingest` |
| Document ID | UUID4 generated per document |
| Phase 1 | Chunking runs; Qdrant upsert is stubbed |
| Phase 2 | Real Qdrant upsert via `qdrant-client` |

---

## Chunking

| Parameter | Default | Notes |
|---|---|---|
| chunk_size | 512 chars | Target chunk length |
| overlap | 64 chars | Overlap between consecutive chunks |
| strategy | Fixed-size | Phase 2: recursive or semantic splitting |

---

## Embeddings

| Parameter | Value |
|---|---|
| Model | `text-embedding-3-small` (OpenAI) |
| Dimension | 1536 |
| Phase 1 | Returns zero vectors (stub) |
| Phase 2 | Real OpenAI API call |

---

## Qdrant Collection

| Parameter | Value |
|---|---|
| Collection name | `nexus_documents` |
| Distance metric | Cosine |
| Vector dimension | 1536 |
| Payload fields | `document_id`, `source`, `chunk_index`, `text`, `metadata` |

---

## Semantic Search

| Parameter | Default |
|---|---|
| top_k | 5 (configurable via `RetrievalPolicy`) |
| min_score | 0.6 |
| Phase 1 | Returns empty list (stub) |
| Phase 2 | Real Qdrant search |

---

## Context Formatting

Retrieved chunks are concatenated with `\n\n` separator and injected as a system message before the user's query. The support and research agents consume this formatted context block.
