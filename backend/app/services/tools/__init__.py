"""
Tools package — registers all core tools into the global tool_registry on import.

Import this module (or any tool directly) to ensure the registry is populated.
"""

from app.services.tools.registry import tool_registry
from app.services.tools.get_conversation_history import get_conversation_history_tool
from app.services.tools.search_knowledge_base import search_knowledge_base_tool
from app.services.tools.summarize_conversation import summarize_conversation_tool
from app.services.tools.trigger_escalation import trigger_escalation_tool
from app.services.tools.get_user_context import get_user_context_tool

# Register all core tools
tool_registry.register(get_conversation_history_tool)
tool_registry.register(search_knowledge_base_tool)
tool_registry.register(summarize_conversation_tool)
tool_registry.register(trigger_escalation_tool)
tool_registry.register(get_user_context_tool)

__all__ = [
    "tool_registry",
    "get_conversation_history_tool",
    "search_knowledge_base_tool",
    "summarize_conversation_tool",
    "trigger_escalation_tool",
    "get_user_context_tool",
]
