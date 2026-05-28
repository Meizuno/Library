from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AddBookCommand:
    title: str
    author: str
    isbn: str
    description: str = ""


@dataclass(frozen=True)
class UpdateBookCommand:
    book_id: UUID
    title: str
    author: str
    description: str
