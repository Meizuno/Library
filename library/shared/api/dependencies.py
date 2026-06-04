from functools import lru_cache
from typing import AsyncGenerator

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from library.auth.ports import CredentialVerifier
from library.book.ports import BookAvailability
from library.loan.repositories import LoanBookAvailability, SqlLoanRepository
from library.member.repositories import (
    CachedMemberRepository,
    MemberCredentialVerifier,
    SqlMemberRepository,
)
from library.notification.email_notifier import EmailNotifier
from library.notification.ports import Notifier
from library.shared.adapters import (
    Argon2PasswordHasher,
    RedisCache,
    SystemClock,
)
from library.shared.config import Settings
from library.shared.ports import Cache, Clock, PasswordHasher


@lru_cache
def get_settings() -> Settings:
    return Settings()


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(request.app.state.engine) as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_redis_client(request: Request) -> Redis:
    return request.app.state.redis


def get_cache(
    redis: Redis = Depends(get_redis_client),
    settings: Settings = Depends(get_settings),
) -> Cache:
    return RedisCache(redis, settings.cache_ttl)


def get_clock() -> Clock:
    return SystemClock()


@lru_cache
def get_password_hasher() -> PasswordHasher:
    return Argon2PasswordHasher()


def get_notifier(settings: Settings = Depends(get_settings)) -> Notifier:
    return EmailNotifier(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        sender=settings.smtp_from,
        username=settings.smtp_username,
        password=settings.smtp_password,
        use_tls=settings.smtp_use_tls,
    )


def get_credential_verifier(
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
    hasher: PasswordHasher = Depends(get_password_hasher),
) -> CredentialVerifier:
    """Bridge `auth.ports.CredentialVerifier` to its impl in the member
    module. Wiring lives here (composition root) so auth/ never imports
    from member/.

    NOTE: the CachedMemberRepository(SqlMemberRepository(session), cache)
    construction mirrors library.member.api.dependencies.get_member_repo
    — inlined here to avoid a circular import between the two modules
    (member.api.dependencies imports cross-cutting providers from this
    file). Keep them in sync.
    """
    member_repo = CachedMemberRepository(SqlMemberRepository(session), cache)
    return MemberCredentialVerifier(member_repo, hasher)


def get_book_availability(
    session: AsyncSession = Depends(get_session),
) -> BookAvailability:
    """Bridge `book.ports.BookAvailability` port to its impl in the loan
    module. Composition root keeps the cross-module wiring here so book/
    never has to import from loan/."""
    return LoanBookAvailability(SqlLoanRepository(session))
