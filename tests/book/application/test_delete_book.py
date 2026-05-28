from uuid import uuid4

import pytest

from library.book.application import DeleteBookUseCase
from library.book.domain import Book, BookNotFound, BookRepository


class TestDeleteBookUseCase:
    async def test_delete_existing_book(
        self, book_repo_with_book: BookRepository, valid_book: Book
    ):
        use_case = DeleteBookUseCase(book_repo_with_book)
        await use_case.execute(valid_book.id)
        assert await book_repo_with_book.find_by_id(valid_book.id) is None

    async def test_delete_missing_book_raises(
        self, book_repo: BookRepository
    ):
        use_case = DeleteBookUseCase(book_repo)
        with pytest.raises(BookNotFound):
            await use_case.execute(uuid4())
