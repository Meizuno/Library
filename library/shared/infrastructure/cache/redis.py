import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError


logger = structlog.get_logger(__name__)


class RedisCache:
    def __init__(self, client: Redis, ttl: int):
        self._client = client
        self._ttl = ttl

    async def get(self, key: str) -> str | None:
        try:
            raw = await self._client.get(key)
        except RedisError as exc:
            logger.warning("redis_get_failed", key=key, error=str(exc))
            return None
        if raw is None:
            return None
        return raw.decode() if isinstance(raw, bytes) else raw

    async def set(self, key: str, value: str) -> None:
        try:
            await self._client.set(key, value, ex=self._ttl)
        except RedisError as exc:
            logger.warning("redis_set_failed", key=key, error=str(exc))

    async def delete(self, key: str) -> None:
        try:
            await self._client.delete(key)
        except RedisError as exc:
            logger.warning("redis_delete_failed", key=key, error=str(exc))
