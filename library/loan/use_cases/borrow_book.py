from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from library.book.exceptions import BookNotAvailable, BookNotFound
from library.book.ports import BookRepository
from library.loan.models import Loan
from library.loan.ports import LoanRepository
from library.member.exceptions import MemberNotFound
from library.member.ports import MemberRepository
from library.shared.application import Clock


@dataclass(frozen=True)
class BorrowBookCommand:
    book_id: UUID
    member_id: UUID


class BorrowBookUseCase:
    def __init__(
        self,
        books: BookRepository,
        members: MemberRepository,
        loans: LoanRepository,
        clock: Clock,
        loan_period_days: int = 14,
    ):
        self._books = books
        self._members = members
        self._loans = loans
        self._clock = clock
        self._loan_period_days = loan_period_days

    async def execute(self, command: BorrowBookCommand) -> Loan:
        book = await self._books.find_by_id(command.book_id)
        if book is None:
            raise BookNotFound(f"Book {command.book_id} not found")

        member = await self._members.find_by_id(command.member_id)
        if member is None:
            raise MemberNotFound(f"Member {command.member_id} not found")

        active_loan = await self._loans.find_active_by_book(command.book_id)
        if active_loan is not None:
            raise BookNotAvailable(
                f"Book {command.book_id} is already loaned"
            )

        now = self._clock.now()
        loan = Loan(
            book_id=command.book_id,
            member_id=command.member_id,
            loaned_at=now,
            due_at=now + timedelta(days=self._loan_period_days),
        )
        await self._loans.create(loan)
        return loan
