from typing import AsyncGenerator

import pytest
from fakeredis import FakeAsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from library.member.domain import Member, MemberRepository
from library.member.infrastructure import (
    CachedMemberRepository,
    InMemoryMemberRepository,
    SqlMemberRepository,
)
from library.shared.infrastructure import metadata
from library.shared.infrastructure.cache import InMemoryCache, RedisCache


@pytest.fixture
async def sql_member_repo() -> AsyncGenerator[SqlMemberRepository, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    session = AsyncSession(engine)
    yield SqlMemberRepository(session)
    await session.close()
    await engine.dispose()


@pytest.fixture(params=["in_memory", "sql", "cache_redis", "cache_in_memory"])
async def empty_member_repo(
    request, sql_member_repo: SqlMemberRepository
) -> AsyncGenerator[MemberRepository, None]:
    if request.param == "in_memory":
        yield InMemoryMemberRepository()
    elif request.param == "sql":
        yield sql_member_repo
    elif request.param == "cache_redis":
        yield CachedMemberRepository(
            sql_member_repo, RedisCache(FakeAsyncRedis(), 300)
        )
    elif request.param == "cache_in_memory":
        yield CachedMemberRepository(sql_member_repo, InMemoryCache(100))


@pytest.fixture
async def member_repo_with_member(
    empty_member_repo: MemberRepository,
    valid_member: Member,
) -> MemberRepository:
    """Repository з одним попередньо збереженим valid_member."""
    await empty_member_repo.create(valid_member)
    return empty_member_repo
