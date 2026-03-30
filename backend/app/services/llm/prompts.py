"""
Prompt Templates — centralized definitions for all LLM prompts.

Keep prompts versioned and testable. Each function returns a list of
message dicts ready to pass to the OpenAI chat API.
"""

SYSTEM_SUPPORT = """\
You are a knowledgeable and helpful support agent for Nexus AI.
Answer the user's question accurately and concisely using the provided context.
If you are unsure, say so and offer to escalate.
"""

SYSTEM_RESEARCH = """\
You are a research specialist. Analyze the provided context thoroughly
and synthesize a comprehensive, well-structured answer.
Cite relevant sections when possible.
"""

SYSTEM_SUMMARIZER = """\
You are a summarization expert. Condense the provided conversation or content
into a clear, accurate summary. Preserve key facts and action items.
"""

SYSTEM_PLANNER = """\
You are a strategic planning assistant. Break down the user's goal into
clear, numbered, actionable steps. Be specific and practical.
"""


def build_support_prompt(message: str, context: str = "", history: list[dict] | None = None) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_SUPPORT}]
    if history:
        messages.extend(history[-10:])  # last 10 turns
    if context:
        messages.append({"role": "system", "content": f"Relevant context:\n{context}"})
    messages.append({"role": "user", "content": message})
    return messages


def build_research_prompt(message: str, context: str = "") -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_RESEARCH}]
    if context:
        messages.append({"role": "system", "content": f"Retrieved documents:\n{context}"})
    messages.append({"role": "user", "content": message})
    return messages


def build_summarizer_prompt(history: list[dict]) -> list[dict]:
    conversation_text = "\n".join(
        f"{turn['role'].upper()}: {turn['content']}" for turn in history
    )
    return [
        {"role": "system", "content": SYSTEM_SUMMARIZER},
        {"role": "user", "content": f"Summarize this conversation:\n\n{conversation_text}"},
    ]


def build_planner_prompt(goal: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PLANNER},
        {"role": "user", "content": f"Create a plan for: {goal}"},
    ]
