"""
Tool Registry — global registry for all registered Nexus AI tools.

Usage:
    from app.services.tools.registry import tool_registry

    tool_registry.register(my_tool)
    tool = tool_registry.get("my_tool_name")
    all_tools = tool_registry.list_tools()
"""

from typing import Any

from app.core.logger import get_logger
from app.services.tools.base_tool import BaseTool

logger = get_logger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance. Overwrites any existing tool with the same name."""
        if tool.name in self._tools:
            logger.warning(
                "tool_registry.overwrite",
                extra={"tool": tool.name},
            )
        self._tools[tool.name] = tool
        logger.debug("tool_registry.registered", extra={"tool": tool.name})

    def get(self, name: str) -> BaseTool | None:
        """Return the tool with the given name, or None if not registered."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """Return a list of dicts describing all registered tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# Module-level singleton
tool_registry = ToolRegistry()
