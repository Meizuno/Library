from typing import AsyncGenerator

import pytest
from fakeredis import FakeAsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from library.book.models import Book
from library.book.ports import BookRepository
from library.book.repositories import CachedBookRepository, SqlBookRepository
from library.shared.infrastructure import metadata
from library.shared.infrastructure.cache import InMemoryCache, RedisCache


@pytest.fixture
async def sql_book_repo() -> AsyncGenerator[SqlBookRepository, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    session = AsyncSession(engine)
    yield SqlBookRepository(session)
    await session.close()
    await engine.dispose()


@pytest.fixture(params=["sql", "cache_redis", "cache_in_memory"])
async def empty_book_repo(
    request, sql_book_repo: SqlBookRepository
) -> AsyncGenerator[BookRepository, None]:
    if request.param == "sql":
        yield sql_book_repo
    elif request.param == "cache_redis":
        yield CachedBookRepository(
            sql_book_repo, RedisCache(FakeAsyncRedis(), 300)
        )
    elif request.param == "cache_in_memory":
        yield CachedBookRepository(sql_book_repo, InMemoryCache(100))


@pytest.fixture
async def book_repo_with_book(
    empty_book_repo: BookRepository, valid_book: Book
) -> BookRepository:
    """Repository з одним попередньо збереженим valid_book."""
    await empty_book_repo.create(valid_book)
    return empty_book_repo
