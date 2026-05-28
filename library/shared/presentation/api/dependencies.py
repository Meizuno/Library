from functools import lru_cache
from typing import AsyncGenerator

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from library.shared.application import Clock
from library.shared.config import Settings
from library.shared.infrastructure import SystemClock
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
