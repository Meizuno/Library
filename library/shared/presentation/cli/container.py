from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from library.book.domain import BookRepository
from library.book.infrastructure import CachedBookRepository, SqlBookRepository
from library.loan.domain import LoanRepository
from library.loan.infrastructure import SqlLoanRepository
from library.member.domain import MemberRepository
from library.member.infrastructure import (
    CachedMemberRepository,
    SqlMemberRepository,
)
from library.notification.domain import Notifier
from library.notification.infrastructure import EmailNotifier
from library.shared.application import Clock, PasswordHasher
from library.shared.config import Settings
from library.shared.infrastructure import (
    Argon2PasswordHasher,
    SystemClock,
    metadata,
)
from library.shared.infrastructure.cache import RedisCache


@dataclass
class CliContext:
    """Resolved dependencies for one CLI command invocation."""

    books: BookRepository
    members: MemberRepository
    loans: LoanRepository
    clock: Clock
    hasher: PasswordHasher
    notifier: Notifier


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
                hasher=Argon2PasswordHasher(),
                notifier=EmailNotifier(
                    smtp_host=settings.smtp_host,
                    smtp_port=settings.smtp_port,
                    sender=settings.smtp_from,
                    username=settings.smtp_username,
                    password=settings.smtp_password,
                    use_tls=settings.smtp_use_tls,
                ),
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
