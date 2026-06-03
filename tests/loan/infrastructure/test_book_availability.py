"""Contract tests for LoanBookAvailability — the loan-slice impl of
`book.domain.BookAvailability`.

The port's invariant: `is_available(book_id)` returns True iff there
is no active (not-yet-returned) loan referencing the book.
"""
from datetime import datetime, timedelta
from uuid import uuid4

from library.book.ports import BookAvailability
from library.loan.domain import Loan, LoanRepository
from library.loan.infrastructure import LoanBookAvailability


class TestLoanBookAvailability:
    def test_satisfies_book_availability_protocol(
        self, loan_repo: LoanRepository
    ):
        availability: BookAvailability = LoanBookAvailability(loan_repo)
        assert hasattr(availability, "is_available")

    async def test_unknown_book_is_available(
        self, loan_repo: LoanRepository
    ):
        # No loans seeded → any book id reads as available.
        availability = LoanBookAvailability(loan_repo)
        assert await availability.is_available(uuid4()) is True

    async def test_book_with_active_loan_is_not_available(
        self, loan_repo: LoanRepository
    ):
        book_id = uuid4()
        loaned_at = datetime(2026, 5, 1, 10, 0, 0)
        active_loan = Loan(
            book_id=book_id,
            member_id=uuid4(),
            loaned_at=loaned_at,
            due_at=loaned_at + timedelta(days=14),
            # returned_at is None by default → loan is active
        )
        await loan_repo.create(active_loan)

        availability = LoanBookAvailability(loan_repo)
        assert await availability.is_available(book_id) is False

    async def test_book_with_only_returned_loans_is_available(
        self, loan_repo: LoanRepository
    ):
        book_id = uuid4()
        loaned_at = datetime(2026, 5, 1, 10, 0, 0)
        returned_loan = Loan(
            book_id=book_id,
            member_id=uuid4(),
            loaned_at=loaned_at,
            due_at=loaned_at + timedelta(days=14),
            returned_at=loaned_at + timedelta(days=7),
        )
        await loan_repo.create(returned_loan)

        availability = LoanBookAvailability(loan_repo)
        # Past loans don't block availability — only the active one matters.
        assert await availability.is_available(book_id) is True

    async def test_different_book_not_affected_by_another_books_loan(
        self, loan_repo: LoanRepository
    ):
        loaned_book = uuid4()
        loaned_at = datetime(2026, 5, 1, 10, 0, 0)
        await loan_repo.create(
            Loan(
                book_id=loaned_book,
                member_id=uuid4(),
                loaned_at=loaned_at,
                due_at=loaned_at + timedelta(days=14),
            )
        )

        availability = LoanBookAvailability(loan_repo)
        other_book = uuid4()
        assert await availability.is_available(other_book) is True
        assert await availability.is_available(loaned_book) is False
