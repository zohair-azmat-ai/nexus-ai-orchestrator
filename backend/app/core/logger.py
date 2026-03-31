import logging
import sys
from pythonjsonlogger import jsonlogger

from app.core.config import settings

_CONTEXT: dict = {}


def set_log_context(**kwargs: str) -> None:
    """Attach key-value pairs (e.g. correlation_id) to the current log context."""
    _CONTEXT.update(kwargs)


def clear_log_context() -> None:
    _CONTEXT.clear()


class ContextFilter(logging.Filter):
    """Injects shared context fields into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in _CONTEXT.items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


def sanitize_log_value(value: str | None) -> str | None:
    if not value:
        return value

    sanitized = value
    for secret in (settings.openai_api_key, settings.auth_secret_key, settings.qdrant_api_key):
        if secret:
            sanitized = sanitized.replace(secret, "***redacted***")
    return sanitized


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)

    if settings.log_format == "json":
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    handler.setFormatter(formatter)
    handler.addFilter(ContextFilter())
    logger.addHandler(handler)
    logger.propagate = False

    return logger
