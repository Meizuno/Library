from uuid import uuid4

import pytest
from fakeredis import FakeAsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from library.book.exceptions import BookNotFound
from library.book.models import ISBN, Book
from library.book.ports import BookRepository
from library.book.repositories import CachedBookRepository, SqlBookRepository
from library.shared.adapters import RedisCache


class TestProtocolSatisfaction:
    def test_cached_book_repo_satisfies_protocol(self, sql_book_repo):
        repo: BookRepository = CachedBookRepository(
            sql_book_repo, RedisCache(FakeAsyncRedis(), 300)
        )
        assert hasattr(repo, "create")
        assert hasattr(repo, "update")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_by_isbn")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")

    def test_sql_book_repo_satisfies_protocol(self):
        repo: BookRepository = SqlBookRepository(AsyncSession())
        assert hasattr(repo, "create")
        assert hasattr(repo, "update")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_by_isbn")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")


class TestBookRepository:
    async def test_get_list_without_book(self, empty_book_repo: BookRepository):
        assert await empty_book_repo.list_all() == []

    async def test_create_book(
        self, empty_book_repo: BookRepository, valid_book: Book
    ):
        await empty_book_repo.create(valid_book)
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
        await book_repo_with_book.update(valid_book)
        saved_book = await book_repo_with_book.find_by_id(valid_book.id)
        assert saved_book.title == "Updated title"

    async def test_update_unsaved_book_raises(
        self, empty_book_repo: BookRepository, valid_book: Book
    ):
        with pytest.raises(BookNotFound):
            await empty_book_repo.update(valid_book)

    async def test_delete_saved_book(
        self, book_repo_with_book: BookRepository, valid_book: Book
    ):
        assert await book_repo_with_book.delete(valid_book.id) is None
        assert await book_repo_with_book.list_all() == []

    async def test_delete_unsaved_book(self, empty_book_repo: BookRepository):
        with pytest.raises(BookNotFound):
            await empty_book_repo.delete(uuid4())


class TestListBooksSearch:
    """Substring-search semantics on `list_all`.

    Same contract across SQL and cached backends:
    - `search` matches case-insensitively
    - matches if the substring appears in EITHER title or author
    - None / empty / whitespace-only `search` means no filter
    """

    @staticmethod
    def _make_book(title: str, author: str, isbn: str) -> Book:
        return Book(title=title, author=author, isbn=ISBN(isbn))

    @pytest.fixture
    async def repo_with_books(
        self, empty_book_repo: BookRepository
    ) -> BookRepository:
        await empty_book_repo.create(
            self._make_book("Harry Potter", "J.K. Rowling", "978-3-16-148410-0")
        )
        await empty_book_repo.create(
            self._make_book("The Hobbit", "J.R.R. Tolkien", "978-3-16-148411-0")
        )
        await empty_book_repo.create(
            self._make_book(
                "Pride and Prejudice", "Jane Austen", "978-3-16-148412-0"
            )
        )
        return empty_book_repo

    async def test_search_none_returns_all(
        self, repo_with_books: BookRepository
    ):
        assert len(await repo_with_books.list_all(search=None)) == 3

    async def test_search_empty_string_returns_all(
        self, repo_with_books: BookRepository
    ):
        assert len(await repo_with_books.list_all(search="")) == 3

    async def test_search_whitespace_only_returns_all(
        self, repo_with_books: BookRepository
    ):
        assert len(await repo_with_books.list_all(search="   ")) == 3

    async def test_search_matches_title_substring(
        self, repo_with_books: BookRepository
    ):
        results = await repo_with_books.list_all(search="potter")
        assert [b.title for b in results] == ["Harry Potter"]

    async def test_search_matches_author_substring(
        self, repo_with_books: BookRepository
    ):
        results = await repo_with_books.list_all(search="rowling")
        assert [b.author for b in results] == ["J.K. Rowling"]

    async def test_search_is_case_insensitive(
        self, repo_with_books: BookRepository
    ):
        upper = await repo_with_books.list_all(search="HARRY")
        lower = await repo_with_books.list_all(search="harry")
        assert {b.id for b in upper} == {b.id for b in lower}
        assert len(upper) == 1

    async def test_search_no_match_returns_empty(
        self, repo_with_books: BookRepository
    ):
        assert await repo_with_books.list_all(search="xyzzy") == []

    async def test_search_matches_either_title_or_author(
        self, repo_with_books: BookRepository
    ):
        # "j" appears in author for all three (J.K., J.R.R., Jane).
        results = await repo_with_books.list_all(search="j")
        assert len(results) == 3

    async def test_search_strips_surrounding_whitespace(
        self, repo_with_books: BookRepository
    ):
        results = await repo_with_books.list_all(search="  potter  ")
        assert [b.title for b in results] == ["Harry Potter"]

    async def test_search_excludes_deleted_books(
        self, repo_with_books: BookRepository
    ):
        # Pre-condition: 'potter' matches the Harry Potter book.
        [book] = await repo_with_books.list_all(search="potter")
        await repo_with_books.delete(book.id)

        assert await repo_with_books.list_all(search="potter") == []
