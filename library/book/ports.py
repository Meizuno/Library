from typing import Protocol
from uuid import UUID

from library.book.models import ISBN, Book


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


class BookAvailability(Protocol):
    """Port for checking whether a book is currently available to borrow.

    A book is **available** when no active (not-yet-returned) Loan
    references it. The truth lives in the loan module — this port lets
    book.api expose availability on BookResponse without book/ importing
    from loan/ (which would invert the established dependency direction).

    The impl lives in `loan/repositories.py` (loan owns the data).
    Composition root wires them — same asymmetric pattern as
    `auth.ports.CredentialVerifier`.
    """

    async def is_available(self, book_id: UUID) -> bool: ...
