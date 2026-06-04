from datetime import datetime
from typing import Any, Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password: str, hashed: str) -> bool: ...


class Logger(Protocol):
    """Port for structured logging.

    First positional argument is the event name (a stable, short string —
    not a human sentence). Keyword arguments are the structured fields.

    Example:
        logger.info("redis_get_failed", key=key, error=str(exc))

    Adapters render the event + fields per their config (console with colors,
    JSON one-line, etc.). See `library.shared.adapters.get_logger` for the
    structlog-backed default and `library.shared.logging_config` for runtime
    configuration.
    """

    def debug(self, event: str, **fields: Any) -> None: ...
    def info(self, event: str, **fields: Any) -> None: ...
    def warning(self, event: str, **fields: Any) -> None: ...
    def error(self, event: str, **fields: Any) -> None: ...
    def exception(self, event: str, **fields: Any) -> None: ...
    def bind(self, **fields: Any) -> "Logger":
        """Return a new logger that includes the given fields on every call."""


class Cache(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str) -> None: ...
    async def delete(self, key: str) -> None: ...
