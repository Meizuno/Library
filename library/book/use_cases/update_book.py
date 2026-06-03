from dataclasses import dataclass
from uuid import UUID

from library.book.exceptions import BookNotFound
from library.book.models import Book
from library.book.ports import BookRepository


@dataclass(frozen=True)
class UpdateBookCommand:
    book_id: UUID
    title: str
    author: str
    description: str


class UpdateBookUseCase:
    def __init__(self, book_repo: BookRepository):
        self._book_repo = book_repo

    async def execute(self, command: UpdateBookCommand) -> Book:
        book = await self._book_repo.find_by_id(command.book_id)
        if book is None:
            raise BookNotFound(f"Book {command.book_id} not found")

        book.title = command.title
        book.author = command.author
        book.description = command.description
        book.validate()

        await self._book_repo.update(book)
        return book
