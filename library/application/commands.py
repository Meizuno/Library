from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AddBookCommand:
    title: str
    author: str
    isbn: str


@dataclass(frozen=True)
class AddMemberCommand:
    name: str
    email: str


@dataclass(frozen=True)
class BorrowBookCommand:
    book_id: UUID
    member_id: UUID


@dataclass(frozen=True)
class ReturnBookCommand:
    loan_id: UUID
