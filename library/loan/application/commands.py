from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class BorrowBookCommand:
    book_id: UUID
    member_id: UUID


@dataclass(frozen=True)
class ReturnBookCommand:
    loan_id: UUID
