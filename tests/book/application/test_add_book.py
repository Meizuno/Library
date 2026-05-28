import pytest

from library.book.application import (
    AddBookCommand,
    AddBookUseCase,
    BookAlreadyExists,
)
from library.book.domain import BookRepository


class TestAddBookUseCase:
    async def test_add_book_success(
        self, book_command: AddBookCommand, book_repo: BookRepository
    ):
        add_book_use_case = AddBookUseCase(book_repo)
        book = await add_book_use_case.execute(book_command)
        assert book == await book_repo.find_by_id(book.id)

    async def test_add_book_duplicate(
        self, book_command: AddBookCommand, book_repo: BookRepository
    ):
        add_book_use_case = AddBookUseCase(book_repo)
        await add_book_use_case.execute(book_command)

        with pytest.raises(BookAlreadyExists):
            await add_book_use_case.execute(book_command)

    async def test_add_book_non_valid_title(
        self, book_repo: BookRepository
    ):
        add_book_use_case = AddBookUseCase(book_repo)
        with pytest.raises(ValueError):
            await add_book_use_case.execute(
                AddBookCommand("", "author", "9783161484100")
            )

    async def test_add_book_non_valid_author(
        self, book_repo: BookRepository
    ):
        add_book_use_case = AddBookUseCase(book_repo)
        with pytest.raises(ValueError):
            await add_book_use_case.execute(
                AddBookCommand("title", "", "9783161484100")
            )

    async def test_add_book_non_valid_isbn(
        self, book_repo: BookRepository
    ):
        add_book_use_case = AddBookUseCase(book_repo)
        with pytest.raises(ValueError):
            await add_book_use_case.execute(
                AddBookCommand("title", "author", "invalid")
            )
