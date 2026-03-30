"""
Prompt Templates — centralized definitions for all agent LLM prompts.

Each builder returns a list[dict] ready to pass to openai_client.complete().
Context (memory, retrieval) is injected as clean blocks — never raw dumps.
"""

# ─── System prompts ───────────────────────────────────────────────────────────

SYSTEM_SUPPORT = """\
You are a knowledgeable and helpful technical support agent for Nexus AI.
Answer the user's question accurately and concisely using the provided context.
Ground your answer in the knowledge base when available.
If you are unsure or the issue is complex, say so clearly and offer next steps.
Keep your response direct and actionable — avoid unnecessary padding."""

SYSTEM_RESEARCH = """\
You are an expert analyst and knowledge synthesizer.
Your job is to explain, compare, and reason through the user's query.
When retrieved documents are available, use them as your primary evidence base.
Structure your answer clearly: start with a direct answer, then supporting detail.
Do not speculate beyond what the evidence supports."""

SYSTEM_SUMMARIZER = """\
You are a concise summarization specialist.
Condense the provided content into a tight, accurate summary.
Preserve all key facts, decisions, and action items.
Format output as short bullet points where appropriate.
Never add information that was not in the source material."""

SYSTEM_PLANNER = """\
You are a strategic planning assistant and execution expert.
Break the user's goal into a clear, numbered, phase-by-phase execution plan.
Each step must be specific, actionable, and sequenced correctly.
Consider dependencies and surface any risks or prerequisites.
Be concise — quality of steps matters more than quantity."""

SYSTEM_ESCALATION = """\
You are a professional risk and escalation handler.
Your role is to acknowledge the user's urgency or concern with empathy,
clearly communicate that the matter is being escalated for human review,
and provide a calm, professional response that de-escalates tension.
Do NOT make promises you cannot keep. Do NOT dismiss the concern.
Keep your response brief, empathetic, and action-oriented."""


# ─── Context injection helpers ────────────────────────────────────────────────

def _memory_block(memory: dict) -> str:
    """Render memory context as a clean, readable block."""
    parts = []
    summary = memory.get("summary_text")
    recent = memory.get("recent_messages", [])

    if summary:
        parts.append(f"[Conversation summary]\n{summary}")
    if recent:
        turns = "\n".join(
            f"  {m['role'].upper()}: {m['content'][:200]}{'...' if len(m['content']) > 200 else ''}"
            for m in recent[-5:]
        )
        parts.append(f"[Recent messages]\n{turns}")

    return "\n\n".join(parts)


def _retrieval_block(retrieval_context: str) -> str:
    """Wrap retrieval context with a clear label."""
    if not retrieval_context.strip():
        return ""
    return f"[Knowledge base]\n{retrieval_context.strip()}"


def _context_message(memory: dict | None, retrieval_context: str) -> dict | None:
    """Build a single context system message, or None if nothing to inject."""
    parts = []
    if memory:
        mem = _memory_block(memory)
        if mem:
            parts.append(mem)
    if retrieval_context:
        ret = _retrieval_block(retrieval_context)
        if ret:
            parts.append(ret)
    if not parts:
        return None
    return {"role": "system", "content": "\n\n".join(parts)}


# ─── Per-agent prompt builders ────────────────────────────────────────────────

def build_support_prompt(
    message: str,
    retrieval_context: str = "",
    memory: dict | None = None,
) -> list[dict]:
    """
    Support agent prompt: grounded, actionable, uses memory + retrieval.
    """
    messages: list[dict] = [{"role": "system", "content": SYSTEM_SUPPORT}]
    ctx = _context_message(memory, retrieval_context)
    if ctx:
        messages.append(ctx)
    messages.append({"role": "user", "content": message})
    return messages


def build_research_prompt(
    message: str,
    retrieval_context: str = "",
    memory: dict | None = None,
) -> list[dict]:
    """
    Research agent prompt: analytical, evidence-based, structured.
    """
    messages: list[dict] = [{"role": "system", "content": SYSTEM_RESEARCH}]
    ctx = _context_message(memory, retrieval_context)
    if ctx:
        messages.append(ctx)
    messages.append({"role": "user", "content": message})
    return messages


def build_summarizer_prompt(
    message: str,
    retrieval_context: str = "",
    memory: dict | None = None,
) -> list[dict]:
    """
    Summarizer agent prompt: condenses available content into bullet points.
    Injects memory history and/or retrieval context as the source material.
    """
    messages: list[dict] = [{"role": "system", "content": SYSTEM_SUMMARIZER}]
    ctx = _context_message(memory, retrieval_context)
    if ctx:
        messages.append(ctx)
    messages.append({"role": "user", "content": f"Please summarize: {message}"})
    return messages


def build_planner_prompt(
    message: str,
    retrieval_context: str = "",
    memory: dict | None = None,
) -> list[dict]:
    """
    Planner agent prompt: structured execution plan for the user's goal.
    """
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PLANNER}]
    ctx = _context_message(memory, retrieval_context)
    if ctx:
        messages.append(ctx)
    messages.append({"role": "user", "content": f"Create a plan for: {message}"})
    return messages


def build_escalation_prompt(
    message: str,
    retrieval_context: str = "",
    memory: dict | None = None,
    detected_reason: str = "high-priority request",
) -> list[dict]:
    """
    Escalation agent prompt: empathetic, professional, action-oriented response.
    """
    messages: list[dict] = [{"role": "system", "content": SYSTEM_ESCALATION}]
    ctx = _context_message(memory, retrieval_context)
    if ctx:
        messages.append(ctx)
    messages.append({
        "role": "user",
        "content": (
            f"Escalation reason: {detected_reason}\n"
            f"User message: {message}"
        ),
    })
    return messages
