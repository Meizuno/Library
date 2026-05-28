from uuid import UUID
from pydantic import BaseModel

from library.book.domain import Book


class BookResponse(BaseModel):
    id: UUID
    title: str
    author: str
    isbn: str
    description: str

    @classmethod
    def from_domain(cls, book: Book) -> "BookResponse":
        return cls(
            id=book.id,
            title=book.title,
            author=book.author,
            isbn=book.isbn.value,
            description=book.description,
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
