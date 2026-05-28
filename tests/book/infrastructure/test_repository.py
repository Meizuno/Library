from uuid import uuid4

import pytest
from fakeredis import FakeAsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from library.book.domain import ISBN, Book, BookNotFound, BookRepository
from library.book.infrastructure import (
    CachedBookRepository,
    InMemoryBookRepository,
    SqlBookRepository,
)
from library.shared.infrastructure.cache import RedisCache


class TestProtocolSatisfaction:
    def test_in_memory_book_repo_satisfies_protocol(self):
        repo: BookRepository = InMemoryBookRepository()
        assert hasattr(repo, "save")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_by_isbn")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")

    def test_cached_book_repo_satisfies_protocol(self, sql_book_repo):
        repo: BookRepository = CachedBookRepository(
            sql_book_repo, RedisCache(FakeAsyncRedis(), 300)
        )
        assert hasattr(repo, "save")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_by_isbn")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")

    def test_sql_book_repo_satisfies_protocol(self):
        repo: BookRepository = SqlBookRepository(AsyncSession())
        assert hasattr(repo, "save")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_by_isbn")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")


class TestBookRepository:
    async def test_get_list_without_book(self, empty_book_repo: BookRepository):
        assert await empty_book_repo.list_all() == []

    async def test_save_book(
        self, empty_book_repo: BookRepository, valid_book: Book
    ):
        await empty_book_repo.save(valid_book)
        await empty_book_repo.list_all()
        assert await empty_book_repo.find_by_id(valid_book.id) == valid_book

    async def test_read_unsaved_book(self, empty_book_repo: BookRepository):
        assert await empty_book_repo.find_by_id(uuid4()) is None

    async def test_read_book_by_isbn(
        self,
        book_repo_with_book: BookRepository,
        valid_book: Book,
        valid_isbn: ISBN,
    ):
        assert await book_repo_with_book.find_by_isbn(valid_isbn) == valid_book

    async def test_get_list_saved_book(
        self, book_repo_with_book: BookRepository, valid_book: Book
    ):
        assert await book_repo_with_book.list_all() == [valid_book]

    async def test_get_immutable_list_saved_book(
        self, book_repo_with_book: BookRepository, valid_book: Book
    ):
        book_list = await book_repo_with_book.list_all()
        book_list.append(valid_book)
        assert await book_repo_with_book.list_all() == [valid_book]

    async def test_update_saved_book(
        self, book_repo_with_book: BookRepository, valid_book: Book
    ):
        valid_book.title = "Updated title"
        await book_repo_with_book.save(valid_book)
        saved_book = await book_repo_with_book.find_by_id(valid_book.id)
        assert saved_book.title == "Updated title"

    async def test_delete_saved_book(
        self, book_repo_with_book: BookRepository, valid_book: Book
    ):
        assert await book_repo_with_book.delete(valid_book.id) is None
        assert await book_repo_with_book.list_all() == []

    async def test_delete_unsaved_book(self, empty_book_repo: BookRepository):
        with pytest.raises(BookNotFound):
            await empty_book_repo.delete(uuid4())
