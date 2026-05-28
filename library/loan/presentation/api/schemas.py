from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from library.loan.domain import Loan


class LoanResponse(BaseModel):
    id: UUID
    book_id: UUID
    member_id: UUID
    loaned_at: datetime
    due_at: datetime
    returned_at: datetime | None

    @classmethod
    def from_domain(cls, loan: Loan) -> "LoanResponse":
        return cls(
            id=loan.id,
            book_id=loan.book_id,
            member_id=loan.member_id,
            loaned_at=loan.loaned_at,
            due_at=loan.due_at,
            returned_at=loan.returned_at,
        )


class BorrowBookCreate(BaseModel):
    book_id: UUID
    member_id: UUID
