from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from library.book.domain import Book
from library.loan.application import ReturnBookCommand, ReturnBookUseCase
from library.loan.domain import Loan, LoanNotFound, LoanRepository
from library.shared.application import Clock


@pytest.fixture
async def loan_repo_with_active_loan(
    loan_repo: LoanRepository, valid_book: Book
) -> tuple[LoanRepository, Loan]:
    loaned_at = datetime(2026, 5, 1, 10, 0, 0)
    loan = Loan(
        book_id=valid_book.id,
        member_id=uuid4(),
        loaned_at=loaned_at,
        due_at=loaned_at + timedelta(days=14),
    )
    await loan_repo.save(loan)
    return loan_repo, loan


class TestReturnBookUseCase:
    async def test_return_book_success(
        self,
        loan_repo_with_active_loan: tuple[LoanRepository, Loan],
        clock: Clock,
        now: datetime,
    ):
        loan_repo, loan = loan_repo_with_active_loan
        use_case = ReturnBookUseCase(loan_repo, clock)

        returned = await use_case.execute(ReturnBookCommand(loan_id=loan.id))

        assert returned.is_returned
        assert returned.returned_at == now
        saved = await loan_repo.find_by_id(loan.id)
        assert saved.returned_at == now

    async def test_return_book_marks_book_available_again(
        self,
        loan_repo_with_active_loan: tuple[LoanRepository, Loan],
        clock: Clock,
    ):
        loan_repo, loan = loan_repo_with_active_loan
        assert await loan_repo.find_active_by_book(loan.book_id) is not None

        use_case = ReturnBookUseCase(loan_repo, clock)
        await use_case.execute(ReturnBookCommand(loan_id=loan.id))

        assert await loan_repo.find_active_by_book(loan.book_id) is None

    async def test_return_missing_loan_raises(
        self, loan_repo: LoanRepository, clock: Clock
    ):
        use_case = ReturnBookUseCase(loan_repo, clock)

        with pytest.raises(LoanNotFound):
            await use_case.execute(ReturnBookCommand(loan_id=uuid4()))

    async def test_return_already_returned_raises(
        self,
        loan_repo_with_active_loan: tuple[LoanRepository, Loan],
        clock: Clock,
    ):
        loan_repo, loan = loan_repo_with_active_loan
        use_case = ReturnBookUseCase(loan_repo, clock)
        await use_case.execute(ReturnBookCommand(loan_id=loan.id))

        with pytest.raises(ValueError):
            await use_case.execute(ReturnBookCommand(loan_id=loan.id))
