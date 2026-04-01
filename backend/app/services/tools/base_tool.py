"""
BaseTool — abstract base class for all Nexus AI tools.

Every tool must define:
  - name         : unique identifier used in registry lookups
  - description  : human-readable purpose (shown in tool listings)
  - input_schema : dict describing expected kwargs (documentation only)
  - execute()    : async implementation

Callers should use call() rather than execute() directly so logging
and error handling are applied consistently.
"""

from abc import ABC, abstractmethod
from typing import Any
import time

from app.core.logger import get_logger
from app.services.events import logger as event_logger
from app.services.events.types import EVENT_TOOL_CALLED, EVENT_TOOL_ERROR, EVENT_TOOL_RESULT

logger = get_logger(__name__)


class BaseTool(ABC):
    name: str = "base_tool"
    description: str = ""

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return a dict describing the expected kwargs for this tool."""
        return {}

    @abstractmethod
    async def execute(self, **kwargs) -> dict[str, Any]:
        """
        Run the tool logic and return a result dict.

        Raises on unrecoverable errors — call() wraps this with logging.
        """

    async def call(self, **kwargs) -> dict[str, Any]:
        """
        Public entry point: log, execute, log result or error.

        Always use this method rather than execute() directly.
        """
        start = time.monotonic()
        logger.info(
            "tool.called",
            extra={"tool": self.name, "kwargs_keys": list(kwargs.keys())},
        )
        event_logger.emit(
            EVENT_TOOL_CALLED,
            stage="tool",
            component=self.name,
            status="success",
            kwargs_keys=list(kwargs.keys()),
        )
        try:
            result = await self.execute(**kwargs)
            latency_ms = (time.monotonic() - start) * 1000
            logger.info(
                "tool.result",
                extra={"tool": self.name, "result_keys": list(result.keys())},
            )
            event_logger.emit(
                EVENT_TOOL_RESULT,
                stage="tool",
                component=self.name,
                status="success",
                latency_ms=round(latency_ms, 2),
                result_keys=list(result.keys()),
            )
            return result
        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000
            logger.error(
                "tool.error",
                extra={"tool": self.name, "error": str(exc)},
            )
            event_logger.emit(
                EVENT_TOOL_ERROR,
                stage="tool",
                component=self.name,
                status="fail",
                latency_ms=round(latency_ms, 2),
                error=str(exc),
            )
            raise

    def __repr__(self) -> str:
        return f"<Tool name={self.name!r}>"
