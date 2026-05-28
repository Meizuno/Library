from uuid import UUID
from pydantic import BaseModel

from library.book.domain import Book


class BookResponse(BaseModel):
    id: UUID
    title: str
    author: str
    isbn: str

    @classmethod
    def from_domain(cls, book: Book) -> "BookResponse":
        return cls(
            id=book.id,
            title=book.title,
            author=book.author,
            isbn=book.isbn.value,
        )


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str
