"""SQL-specific tests for soft-delete semantics on SqlBookRepository.

The parametrized contract suite in test_contract.py verifies the
*observable* repository behavior (after delete, find returns None;
list excludes it). These tests pin down the SQL-impl detail that
delete is *soft* — the row stays physically present with `deleted_at`
stamped — and the related secondary guarantees (find_by_isbn skips
soft-deleted rows, update on a soft-deleted row raises, double-delete
raises).
"""
from typing import AsyncGenerator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from library.book.exceptions import BookNotFound
from library.book.models import Book
from library.book.repositories import SqlBookRepository, books_table
from library.shared.adapters import metadata


@pytest.fixture
async def sql_repo_and_session() -> AsyncGenerator[
    tuple[SqlBookRepository, AsyncSession], None
]:
    """SqlBookRepository plus a handle on its session, so tests can
    issue raw SELECTs that bypass the repository's `deleted_at IS NULL`
    filter and observe the physical row state."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    session = AsyncSession(engine)
    yield SqlBookRepository(session), session
    await session.close()
    await engine.dispose()


class TestSoftDeleteBook:
    async def test_delete_keeps_row_physically_present_with_deleted_at(
        self,
        sql_repo_and_session,
        valid_book: Book,
    ):
        repo, session = sql_repo_and_session
        await repo.create(valid_book)

        await repo.delete(valid_book.id)

        # Direct SELECT bypassing the repo's filter — proves the row
        # is still in the table.
        row = (
            await session.execute(
                select(books_table).where(books_table.c.id == valid_book.id)
            )
        ).first()
        assert row is not None
        assert row.deleted_at is not None

    async def test_delete_then_find_by_isbn_returns_none(
        self,
        sql_repo_and_session,
        valid_book: Book,
    ):
        repo, _ = sql_repo_and_session
        await repo.create(valid_book)
        await repo.delete(valid_book.id)

        assert await repo.find_by_isbn(valid_book.isbn) is None

    async def test_update_on_soft_deleted_book_raises(
        self,
        sql_repo_and_session,
        valid_book: Book,
    ):
        repo, _ = sql_repo_and_session
        await repo.create(valid_book)
        await repo.delete(valid_book.id)

        valid_book.title = "Different title"
        with pytest.raises(BookNotFound):
            await repo.update(valid_book)

    async def test_double_delete_raises(
        self,
        sql_repo_and_session,
        valid_book: Book,
    ):
        repo, _ = sql_repo_and_session
        await repo.create(valid_book)
        await repo.delete(valid_book.id)

        with pytest.raises(BookNotFound):
            await repo.delete(valid_book.id)
