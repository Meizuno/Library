from uuid import UUID

from pydantic import BaseModel

from library.book.models import Book


class BookResponse(BaseModel):
    """Response shape shared across all book routes (read, list, add, update).

    Per-route REQUEST shapes (BookCreate, BookUpdate) live with their route
    in api/routes/*.py — they're route-local. The response shape is the
    same across reads and writes and lives here to stay DRY.
    """

    id: UUID
    title: str
    author: str
    isbn: str
    description: str
    is_available: bool

    @classmethod
    def from_domain(
        cls, book: Book, *, is_available: bool
    ) -> "BookResponse":
        return cls(
            id=book.id,
            title=book.title,
            author=book.author,
            isbn=book.isbn.value,
            description=book.description,
            is_available=is_available,
        )
