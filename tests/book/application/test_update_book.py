from uuid import uuid4

import pytest

from library.book.application import UpdateBookCommand, UpdateBookUseCase
from library.book.domain import Book, BookNotFound, BookRepository


class TestUpdateBookUseCase:
    async def test_update_existing_book(
        self, book_repo_with_book: BookRepository, valid_book: Book
    ):
        use_case = UpdateBookUseCase(book_repo_with_book)

        updated = await use_case.execute(
            UpdateBookCommand(
                book_id=valid_book.id,
                title="New Title",
                author="New Author",
                description="A new description",
            )
        )

        assert updated.title == "New Title"
        assert updated.author == "New Author"
        assert updated.description == "A new description"
        saved = await book_repo_with_book.find_by_id(valid_book.id)
        assert saved.title == "New Title"
        assert saved.author == "New Author"
        assert saved.description == "A new description"

    async def test_update_preserves_isbn(
        self, book_repo_with_book: BookRepository, valid_book: Book
    ):
        original_isbn = valid_book.isbn
        use_case = UpdateBookUseCase(book_repo_with_book)

        updated = await use_case.execute(
            UpdateBookCommand(
                book_id=valid_book.id,
                title="T",
                author="A",
                description="",
            )
        )

        assert updated.isbn == original_isbn

    async def test_update_missing_book_raises(
        self, book_repo: BookRepository
    ):
        use_case = UpdateBookUseCase(book_repo)
        with pytest.raises(BookNotFound):
            await use_case.execute(
                UpdateBookCommand(
                    book_id=uuid4(),
                    title="T",
                    author="A",
                    description="",
                )
            )

    async def test_update_invalid_title_raises(
        self, book_repo_with_book: BookRepository, valid_book: Book
    ):
        use_case = UpdateBookUseCase(book_repo_with_book)
        with pytest.raises(ValueError):
            await use_case.execute(
                UpdateBookCommand(
                    book_id=valid_book.id,
                    title="",
                    author="A",
                    description="",
                )
            )
