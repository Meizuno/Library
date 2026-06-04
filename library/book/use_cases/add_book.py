from dataclasses import dataclass

from library.book.exceptions import BookAlreadyExists
from library.book.models import ISBN, Book
from library.book.ports import BookRepository


@dataclass(frozen=True)
class AddBookCommand:
    title: str
    author: str
    isbn: str
    description: str = ""


class AddBookUseCase:
    def __init__(self, book_repo: BookRepository):
        self._book_repo = book_repo

    async def execute(self, command: AddBookCommand) -> Book:
        isbn = ISBN(command.isbn)
        if await self._book_repo.find_by_isbn(isbn):
            raise BookAlreadyExists(
                f"Book with ISBN {command.isbn} already exists"
            )

        book = Book(
            title=command.title,
            author=command.author,
            isbn=isbn,
            description=command.description,
        )
        await self._book_repo.create(book)
        return book
