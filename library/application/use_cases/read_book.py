from uuid import UUID

from library.domain import Book, BookRepository


class ReadBookUseCase:
    def __init__(self, book_repo: BookRepository):
        self._book_repo = book_repo

    async def execute(self, book_id: UUID) -> Book | None:
        return await self._book_repo.find_by_id(book_id)
