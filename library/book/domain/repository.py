from uuid import UUID
from typing import Protocol

from library.book.domain.model import Book
from library.book.domain.value_objects import ISBN


class BookRepository(Protocol):
    async def create(self, book: Book) -> None: ...
    async def update(self, book: Book) -> None: ...
    async def find_by_id(self, book_id: UUID) -> Book | None: ...
    async def find_by_isbn(self, isbn: ISBN) -> Book | None: ...
    async def list_all(self, search: str | None = None) -> list[Book]:
        """List books, optionally filtered by a case-insensitive substring
        search against title OR author. None / empty / whitespace-only
        `search` means no filter (returns everything)."""

    async def delete(self, book_id: UUID) -> None: ...
