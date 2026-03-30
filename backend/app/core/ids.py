import uuid
from contextvars import ContextVar

# Holds the correlation ID for the current request context
_correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def generate_id() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def get_correlation_id() -> str:
    return _correlation_id_var.get()


def set_correlation_id(value: str) -> None:
    _correlation_id_var.set(value)


def get_trace_id() -> str:
    """Trace ID currently reuses the request correlation ID."""
    return get_correlation_id()


def set_trace_id(value: str) -> None:
    """Trace ID currently reuses the request correlation ID."""
    set_correlation_id(value)
