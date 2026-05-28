from library.book.domain import Book, ISBN, BookRepository
from library.book.application.commands import AddBookCommand
from library.book.application.exceptions import BookAlreadyExists


class AddBookUseCase:
    def __init__(self, book_repo: BookRepository):
        self._book_repo = book_repo

    async def execute(self, command: AddBookCommand) -> Book:
        isbn = ISBN(command.isbn)
        if await self._book_repo.find_by_isbn(isbn):
            raise BookAlreadyExists(
                f"Book with ISBN {command.isbn} already exists"
            )

        book = Book(title=command.title, author=command.author, isbn=isbn)
        await self._book_repo.create(book)
        return book
