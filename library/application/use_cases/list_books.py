from library.domain import Book, BookRepository


class ListBooksUseCase:
    def __init__(self, book_repo: BookRepository):
        self._book_repo = book_repo

    async def execute(self) -> list[Book]:
        return await self._book_repo.list_all()
