from uuid import UUID

from library.book.domain import Book, ISBN, BookNotFound


class InMemoryBookRepository:
    def __init__(self):
        self._book_db: dict[UUID, Book] = {}

    async def create(self, book: Book) -> None:
        self._book_db[book.id] = book

    async def update(self, book: Book) -> None:
        if book.id not in self._book_db:
            raise BookNotFound(f"Book {book.id} not found")
        self._book_db[book.id] = book

    async def find_by_id(self, book_id: UUID) -> Book | None:
        return self._book_db.get(book_id)

    async def find_by_isbn(self, isbn: ISBN) -> Book | None:
        for book in self._book_db.values():
            if book.isbn == isbn:
                return book
        return None

    async def list_all(self) -> list[Book]:
        return list(self._book_db.values())

    async def delete(self, book_id: UUID) -> None:
        if book_id not in self._book_db:
            raise BookNotFound(f"Book {book_id} not found")

        del self._book_db[book_id]
