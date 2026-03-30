# Nexus AI — Agent Specification

## Agent Design Principles

1. All agents extend `BaseAgent` and implement `async def run(ctx)`
2. Agents receive the full `OrchestratorContext` and return it mutated
3. Agents must populate `ctx["answer"]` before returning
4. Agents should log their execution via `self._log_run(ctx)`
5. Agents must not call the LLM directly in Phase 1 — use stubs

---

## Agent Registry

### Support Agent
- **Name:** `support`
- **Responsibility:** Handle general product/service questions
- **Activation:** Default agent, used when no specific intent is detected
- **Context used:** Conversation history, retrieval context
- **Phase 3:** Builds support prompt with RAG context, calls OpenAI

### Research Agent
- **Name:** `research`
- **Responsibility:** Deep lookup and multi-document synthesis
- **Activation:** Keywords: `research`, `find`, `search`, `what is`
- **Context used:** Retrieval results (multi-document)
- **Phase 3:** Multi-step retrieval + LLM synthesis chain

### Summarizer Agent
- **Name:** `summarizer`
- **Responsibility:** Condense conversations or content
- **Activation:** Keywords: `summarize`, `summary`, `tldr`
- **Context used:** Conversation history
- **Phase 3:** LLM-powered summarization with structured output

### Planner Agent
- **Name:** `planner`
- **Responsibility:** Decompose goals into actionable steps
- **Activation:** Keywords: `plan`, `roadmap`, `steps`, `how to`
- **Context used:** User goal, optionally knowledge base
- **Phase 3:** Chain-of-thought planning prompt with numbered steps

### Escalation Agent
- **Name:** `escalation`
- **Responsibility:** Flag requests for human review
- **Activation:** Keywords: `escalate`, `urgent`, `critical`, `human`; also triggered by low triage confidence
- **Context used:** Full request context
- **Phase 4:** Triggers real escalation webhook or ticketing system

---

## Agent Selection (Triage Stage)

### Phase 1: Keyword Matching
Simple keyword scan of the user message. First match wins. Fallback: `support`.

### Phase 3: LLM-Based Classification
Call OpenAI with intent classification prompt. Returns agent name + confidence score.
If confidence < threshold (default 0.3), fall back to `support` or `escalation`.

---

## Agent Output Contract

Every agent must return the context with:
- `ctx["answer"]` — string response to return to user
- `ctx["selected_agent"]` — unchanged (set by triage stage)
- Any additional context fields the agent modifies (e.g. `ctx["escalated"]`)
