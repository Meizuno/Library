from functools import lru_cache
from typing import AsyncGenerator

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

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
