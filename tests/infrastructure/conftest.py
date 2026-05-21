from typing import AsyncGenerator

import pytest
from fakeredis import FakeAsyncRedis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from library.domain import (
    Book,
    Member,
    Loan,
    BookRepository,
    MemberRepository,
    LoanRepository,
)
from library.infrastructure import (
    InMemoryBookRepository,
    InMemoryMemberRepository,
    InMemoryLoanRepository,
    CachedBookRepository,
    CachedMemberRepository,
    RedisCache,
    InMemoryCache,
)
from library.infrastructure.sql import (
    SqlBookRepository,
    SqlMemberRepository,
    SqlLoanRepository,
)
from library.infrastructure.sql.tables import metadata


@pytest.fixture
async def sql_book_repo() -> AsyncGenerator[SqlBookRepository, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    session = AsyncSession(engine)
    yield SqlBookRepository(session)
    await session.close()
    await engine.dispose()


@pytest.fixture
async def sql_member_repo() -> AsyncGenerator[SqlMemberRepository, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    session = AsyncSession(engine)
    yield SqlMemberRepository(session)
    await session.close()
    await engine.dispose()


@pytest.fixture
async def sql_loan_repo() -> AsyncGenerator[SqlLoanRepository, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    session = AsyncSession(engine)
    yield SqlLoanRepository(session)
    await session.close()
    await engine.dispose()


@pytest.fixture(params=["in_memory", "sql", "cache_redis", "cache_in_memory"])
async def empty_book_repo(
    request, sql_book_repo: SqlBookRepository
) -> AsyncGenerator[BookRepository, None]:
    if request.param == "in_memory":
        yield InMemoryBookRepository()
    elif request.param == "sql":
        yield sql_book_repo
    elif request.param == "cache_redis":
        yield CachedBookRepository(
            sql_book_repo, RedisCache(FakeAsyncRedis(), 300)
        )
    elif request.param == "cache_in_memory":
        yield CachedBookRepository(sql_book_repo, InMemoryCache(100))


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
async def book_repo_with_book(
    empty_book_repo: BookRepository, valid_book: Book
) -> BookRepository:
    """Repository з одним попередньо збереженим valid_book."""
    await empty_book_repo.save(valid_book)
    return empty_book_repo


@pytest.fixture
async def member_repo_with_member(
    empty_member_repo: MemberRepository,
    valid_member: Member,
) -> MemberRepository:
    """Repository з одним попередньо збереженим valid_member."""
    await empty_member_repo.save(valid_member)
    return empty_member_repo


@pytest.fixture(params=["in_memory", "sql"])
async def empty_loan_repo(
    request, sql_loan_repo: SqlLoanRepository
) -> AsyncGenerator[LoanRepository, None]:
    if request.param == "in_memory":
        yield InMemoryLoanRepository()
    elif request.param == "sql":
        yield sql_loan_repo


@pytest.fixture
async def loan_repo_with_loan(
    empty_loan_repo: LoanRepository, valid_loan: Loan
) -> LoanRepository:
    """Repository з одним попередньо збереженим valid_loan."""
    await empty_loan_repo.save(valid_loan)
    return empty_loan_repo
