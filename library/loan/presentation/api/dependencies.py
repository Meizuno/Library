from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from library.book.domain import BookRepository
from library.book.presentation.api.dependencies import get_book_repo
from library.loan.application import BorrowBookUseCase, ReturnBookUseCase
from library.loan.domain import LoanRepository
from library.loan.infrastructure import SqlLoanRepository
from library.member.domain import MemberRepository
from library.member.presentation.api.dependencies import get_member_repo
from library.shared.application import Clock
from library.shared.presentation.api.dependencies import get_clock, get_session


def get_loan_repo(
    session: AsyncSession = Depends(get_session),
) -> LoanRepository:
    return SqlLoanRepository(session)


def get_borrow_book_use_case(
    books: BookRepository = Depends(get_book_repo),
    members: MemberRepository = Depends(get_member_repo),
    loans: LoanRepository = Depends(get_loan_repo),
    clock: Clock = Depends(get_clock),
) -> BorrowBookUseCase:
    return BorrowBookUseCase(books, members, loans, clock)


def get_return_book_use_case(
    loans: LoanRepository = Depends(get_loan_repo),
    clock: Clock = Depends(get_clock),
) -> ReturnBookUseCase:
    return ReturnBookUseCase(loans, clock)
