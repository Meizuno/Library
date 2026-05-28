from functools import lru_cache
from typing import AsyncGenerator

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from library.auth.domain import CredentialVerifier, TokenIssuer
from library.auth.infrastructure import PyJWTTokenIssuer
from library.member.domain import MemberRepository, VerificationTokenIssuer
from library.member.infrastructure import (
    CachedMemberRepository,
    MemberCredentialVerifier,
    PyJWTVerificationTokenIssuer,
    SqlMemberRepository,
)
from library.notification.domain import Notifier
from library.notification.infrastructure import EmailNotifier
from library.shared.application import Clock, PasswordHasher
from library.shared.config import Settings
from library.shared.infrastructure import Argon2PasswordHasher, SystemClock
from library.shared.infrastructure.cache import Cache, RedisCache


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


def get_token_issuer(
    settings: Settings = Depends(get_settings),
) -> TokenIssuer:
    return PyJWTTokenIssuer(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_ttl_minutes=settings.access_token_ttl_minutes,
    )


def get_member_repo(
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
) -> MemberRepository:
    return CachedMemberRepository(SqlMemberRepository(session), cache)


def get_credential_verifier(
    member_repo: MemberRepository = Depends(get_member_repo),
    hasher: PasswordHasher = Depends(get_password_hasher),
) -> CredentialVerifier:
    return MemberCredentialVerifier(member_repo, hasher)


def get_verification_token_issuer(
    settings: Settings = Depends(get_settings),
) -> VerificationTokenIssuer:
    return PyJWTVerificationTokenIssuer(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        ttl_hours=settings.verification_token_ttl_hours,
    )
