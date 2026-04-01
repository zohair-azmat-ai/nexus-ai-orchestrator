# Nexus AI — Memory Specification

## Memory Types

### Short-Term Memory
- **Scope:** Single session (bounded by `session_id`)
- **Content:** Recent message turns (user + assistant)
- **Limit:** Last N turns (default: 20, configurable via `MemoryRules`)
- **Storage:** Phase 1: in-process dict. Phase 2: PostgreSQL `messages` table
- **Usage:** Injected into the LLM prompt as conversation history

### Long-Term Memory
- **Scope:** Per-user across sessions
- **Content:** Compressed summaries of past sessions
- **Storage:** Phase 2: PostgreSQL `user_memory` table
- **Usage:** Injected as a high-level context block in the prompt

### Session Summary
- **Trigger:** Automatically generated when session exceeds `summarize_after_turns` threshold
- **Storage:** Phase 2: stored alongside session record
- **Usage:** Replaces raw history to keep prompt within token limits

---

## Memory Read/Write Flow

### Read (Memory Stage)
1. Load short-term history from store (last N turns)
2. Load session summary if available
3. Apply `MemoryRules.trim_history()` to enforce token limits
4. Return `{ history: [...], summary: str | None }`

### Write (After Response)
1. Append user message to session history
2. Append assistant response to session history
3. If session exceeds `summarize_after_turns`, trigger summarization worker

---

## Memory Rules

| Rule | Default | Description |
|---|---|---|
| max_short_term_turns | 20 | Max turns included in context window |
| summarize_after_turns | 15 | Trigger summarization after this many turns |
| persist_summaries | false (Phase 1) | Whether to write summaries to DB |
| relevance_threshold | 0.5 | Min score for semantic memory retrieval (future) |

---

## Future: Semantic Memory (Phase 6+)
Long-term memory items stored as vectors in Qdrant. At query time, the most relevant memories are retrieved via similarity search and injected into the prompt — similar to RAG but for personal user context.
