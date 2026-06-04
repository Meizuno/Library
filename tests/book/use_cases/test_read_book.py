from uuid import uuid4

from library.book.models import Book
from library.book.ports import BookRepository
from library.book.use_cases.read_book import ReadBookUseCase


class TestReadBookUseCase:
    async def test_read_existing_book(
        self, book_repo_with_book: BookRepository, valid_book: Book
    ):
        use_case = ReadBookUseCase(book_repo_with_book)
        assert await use_case.execute(valid_book.id) == valid_book

    async def test_read_missing_book_returns_none(
        self, book_repo: BookRepository
    ):
        use_case = ReadBookUseCase(book_repo)
        assert await use_case.execute(uuid4()) is None
