from functools import lru_cache
from typing import AsyncGenerator

from fastapi import Request, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from library.config import Settings
from library.infrastructure import (
    Cache,
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
from library.domain import BookRepository, MemberRepository, LoanRepository
from library.application import Clock
from library.application.use_cases import (
    AddBookUseCase,
    ReadBookUseCase,
    ListBooksUseCase,
    DeleteBookUseCase,
    AddMemberUseCase,
    ReadMemberUseCase,
    ListMembersUseCase,
    DeleteMemberUseCase,
    BorrowBookUseCase,
    ReturnBookUseCase,
)


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


def get_book_repo(
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
) -> BookRepository:
    return CachedBookRepository(SqlBookRepository(session), cache)


def get_add_book_use_case(
    book_repo: BookRepository = Depends(get_book_repo),
) -> AddBookUseCase:
    return AddBookUseCase(book_repo)


def get_read_book_use_case(
    book_repo: BookRepository = Depends(get_book_repo),
) -> ReadBookUseCase:
    return ReadBookUseCase(book_repo)


def get_list_books_use_case(
    book_repo: BookRepository = Depends(get_book_repo),
) -> ListBooksUseCase:
    return ListBooksUseCase(book_repo)


def get_delete_book_use_case(
    book_repo: BookRepository = Depends(get_book_repo),
) -> DeleteBookUseCase:
    return DeleteBookUseCase(book_repo)


def get_member_repo(
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
) -> MemberRepository:
    return CachedMemberRepository(SqlMemberRepository(session), cache)


def get_add_member_use_case(
    member_repo: MemberRepository = Depends(get_member_repo),
) -> AddMemberUseCase:
    return AddMemberUseCase(member_repo)


def get_read_member_use_case(
    member_repo: MemberRepository = Depends(get_member_repo),
) -> ReadMemberUseCase:
    return ReadMemberUseCase(member_repo)


def get_list_members_use_case(
    member_repo: MemberRepository = Depends(get_member_repo),
) -> ListMembersUseCase:
    return ListMembersUseCase(member_repo)


def get_delete_member_use_case(
    member_repo: MemberRepository = Depends(get_member_repo),
) -> DeleteMemberUseCase:
    return DeleteMemberUseCase(member_repo)


def get_clock() -> Clock:
    return SystemClock()


def get_loan_repo(
    session: AsyncSession = Depends(get_session),
) -> LoanRepository:
    return SqlLoanRepository(session)


def get_borrow_book_use_case(
    books: BookRepository = Depends(get_book_repo),
    members: MemberRepository = Depends(get_member_repo),
    loans: LoanRepository = Depends(get_loan_repo),
    clock: Clock = Depends(get_clock),
) -> BorrowBookUseCase:
    return BorrowBookUseCase(books, members, loans, clock)


def get_return_book_use_case(
    loans: LoanRepository = Depends(get_loan_repo),
    clock: Clock = Depends(get_clock),
) -> ReturnBookUseCase:
    return ReturnBookUseCase(loans, clock)
