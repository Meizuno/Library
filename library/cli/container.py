from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from library.config import Settings
from library.domain import BookRepository, MemberRepository, LoanRepository
from library.application import Clock
from library.infrastructure import (
    RedisCache,
    CachedBookRepository,
    CachedMemberRepository,
    SystemClock,
)
from library.infrastructure.sql import (
    SqlBookRepository,
    SqlMemberRepository,
    SqlLoanRepository,
)
from library.infrastructure.sql.tables import metadata


@dataclass
class CliContext:
    """Resolved dependencies for one CLI command invocation."""

    books: BookRepository
    members: MemberRepository
    loans: LoanRepository
    clock: Clock


@asynccontextmanager
async def cli_context() -> AsyncIterator[CliContext]:
    """Build a one-shot context for a CLI command.

    Mirrors what FastAPI's per-request `get_session` does:
    open engine + session, commit on success, rollback on exception.
    """
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    redis = Redis.from_url(settings.redis_url)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

        session = AsyncSession(engine)
        try:
            cache = RedisCache(redis, settings.cache_ttl)
            yield CliContext(
                books=CachedBookRepository(SqlBookRepository(session), cache),
                members=CachedMemberRepository(
                    SqlMemberRepository(session), cache
                ),
                loans=SqlLoanRepository(session),
                clock=SystemClock(),
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    finally:
        await redis.aclose()
        await engine.dispose()
