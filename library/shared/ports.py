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


class EventPublisher(Protocol):
    """Port for publishing domain events to in-process subscribers.

    Use cases depend on this narrow write-side interface; the registry of
    handlers lives on the concrete bus (see
    `library.shared.adapters.InProcessEventBus`) and is wired in the
    composition root (`library.shared.api.main` lifespan).

    Adapters are expected to dispatch synchronously and catch handler
    exceptions so a failing subscriber does not roll back the publisher's
    work. That's the EDA tradeoff: registration succeeds even if a
    downstream side-effect (e.g. sending email) fails. A production
    system would back this with an outbox + retry.
    """

    async def publish(self, event: object) -> None: ...


class EventHandler[T](Protocol):
    """Port for reacting to a domain event of type `T`.

    Named-method (`handle`) rather than `__call__` to match every other
    port in this codebase (`Notifier.send`, `Clock.now`, `Cache.get`,
    repository methods, use cases' `execute`). Subscribers register
    with `InProcessEventBus.subscribe(EventType, handler)` and the bus
    dispatches by calling `handler.handle(event)`.

    Handlers are expected to swallow their own retryable failures
    where appropriate (the bus already catches + logs uncaught
    exceptions so one failing handler does not affect the publisher or
    other subscribers).
    """

    async def handle(self, event: T) -> None: ...
