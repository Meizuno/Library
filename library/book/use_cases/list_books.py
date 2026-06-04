from library.book.models import Book
from library.book.ports import BookRepository


class ListBooksUseCase:
    def __init__(self, book_repo: BookRepository):
        self._book_repo = book_repo

    async def execute(self, search: str | None = None) -> list[Book]:
        return await self._book_repo.list_all(search=search)
