"""Concrete adapters for the cross-cutting ports declared in
`library.shared.ports`, plus the shared SQLAlchemy `MetaData` instance
that every feature's `repositories.py` registers its tables with.

All adapters live here together because none of them carries a sibling
that would justify its own file (single Clock impl, single PasswordHasher
impl, etc.). Cache has two impls (Redis + in-memory) but they're tiny
and pair naturally with the Cache Protocol they implement.
"""
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any, cast

import structlog
from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import Argon2Error, InvalidHashError
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import MetaData

from library.shared.ports import Logger

# --- Shared SQLAlchemy metadata --------------------------------------------
# Every feature's repositories.py registers its Table against this single
# MetaData instance so `metadata.create_all(...)` builds the whole schema.
metadata = MetaData()


# --- Clock -----------------------------------------------------------------
class SystemClock:
    def now(self) -> datetime:
        return datetime.now()


# --- Password hasher -------------------------------------------------------
class Argon2PasswordHasher:
    """argon2-cffi adapter for the PasswordHasher port.

    Uses argon2-cffi directly rather than passlib (which depends on the
    removed-in-3.13 `crypt` stdlib module). Argon2id is the default and
    is the current OWASP recommendation for password hashing.

    Note: argon2-cffi's verify(hash, password) takes its arguments in the
    opposite order from this adapter's verify(password, hash). The wrapper
    swaps them so the port stays consistent across implementations.

    Both Argon2Error (wrong password, corrupted hash) and InvalidHashError
    (malformed input) are caught — argon2-cffi quirk: InvalidHashError does
    NOT inherit from Argon2Error, it's a direct subclass of Exception.
    """

    def __init__(self) -> None:
        self._hasher = _Argon2()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        try:
            return self._hasher.verify(hashed, password)
        except (Argon2Error, InvalidHashError):
            return False


# --- Logger ----------------------------------------------------------------
def get_logger(name: str) -> Logger:
    """Return a structlog-backed Logger.

    structlog's BoundLogger structurally satisfies the Logger protocol —
    no wrapper class needed. Configuration (JSON vs console, log level,
    bound contextvars) is handled centrally in
    `library.shared.logging_config.configure_logging` and the HTTP
    middleware.
    """
    # structlog's stubs say get_logger returns Any (the lazy proxy is hard
    # to type precisely); cast back to the Logger Protocol it structurally
    # satisfies after first .bind() or method call.
    return cast(Logger, structlog.get_logger(name))


# --- Cache -----------------------------------------------------------------
class InMemoryCache:
    def __init__(self, max_count: int):
        if max_count <= 0:
            raise ValueError("max_count must be positive")
        self._store: OrderedDict[str, str] = OrderedDict()
        self._max_count = max_count

    async def get(self, key: str) -> str | None:
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        return self._store[key]

    async def set(self, key: str, value: str) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self._max_count:
            self._store.popitem(last=False)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)


_redis_logger = get_logger("library.shared.adapters.redis_cache")


class RedisCache:
    def __init__(self, client: Redis, ttl: int):
        self._client = client
        self._ttl = ttl

    async def get(self, key: str) -> str | None:
        try:
            raw = await self._client.get(key)
        except RedisError as exc:
            _redis_logger.warning("redis_get_failed", key=key, error=str(exc))
            return None
        if raw is None:
            return None
        return raw.decode() if isinstance(raw, bytes) else raw

    async def set(self, key: str, value: str) -> None:
        try:
            await self._client.set(key, value, ex=self._ttl)
        except RedisError as exc:
            _redis_logger.warning("redis_set_failed", key=key, error=str(exc))

    async def delete(self, key: str) -> None:
        try:
            await self._client.delete(key)
        except RedisError as exc:
            _redis_logger.warning(
                "redis_delete_failed", key=key, error=str(exc)
            )


# --- Event bus -------------------------------------------------------------
_event_bus_logger = get_logger("library.shared.adapters.event_bus")


class InProcessEventBus:
    """Synchronous in-process pub/sub for domain events.

    Handlers are dispatched in registration order on the publishing
    coroutine. Each handler is awaited inside a try/except — a failing
    handler is logged at exception level but does NOT propagate to the
    publisher. This is the canonical EDA tradeoff: the publishing
    command (e.g. AddMemberUseCase) succeeds even if a downstream
    side-effect (e.g. sending email) fails.

    Suitable for a study/template project. A production system would
    back this with an outbox table (events persisted in the same
    transaction as the command's state changes) plus a worker that
    retries until delivery succeeds.

    `subscribe` is intentionally NOT on the EventPublisher port — only
    the composition root (lifespan wiring in
    `library.shared.api.main`) registers handlers; use cases see the
    narrow publish-only interface.
    """

    def __init__(self) -> None:
        self._handlers: dict[
            type, list[Callable[[Any], Awaitable[None]]]
        ] = {}

    def subscribe[T](
        self,
        event_type: type[T],
        handler: Callable[[T], Awaitable[None]],
    ) -> None:
        # The dict is heterogeneous (one entry per event type), so we
        # store handlers under their concrete type and cast away the
        # type-parameter at the boundary. Dispatch in `publish` uses
        # `type(event)` to find the matching slot, so the runtime types
        # always line up with what was registered here.
        self._handlers.setdefault(event_type, []).append(
            cast(Callable[[Any], Awaitable[None]], handler)
        )

    async def publish(self, event: object) -> None:
        for handler in self._handlers.get(type(event), []):
            try:
                await handler(event)
            except Exception:
                _event_bus_logger.exception(
                    "event_handler_failed",
                    event_type=type(event).__name__,
                    handler=getattr(handler, "__qualname__", repr(handler)),
                )
