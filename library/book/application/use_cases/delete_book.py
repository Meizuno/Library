from uuid import UUID

from library.book.domain import BookRepository


class DeleteBookUseCase:
    def __init__(self, book_repo: BookRepository):
        self._book_repo = book_repo

    async def execute(self, book_id: UUID) -> None:
        await self._book_repo.delete(book_id)
