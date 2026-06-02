from uuid import UUID
from pydantic import BaseModel

from library.book.domain import Book


class BookResponse(BaseModel):
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


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str
    description: str = ""


class BookUpdate(BaseModel):
    title: str
    author: str
    description: str
