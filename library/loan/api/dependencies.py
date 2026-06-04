from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from library.book.api.dependencies import get_book_repo
from library.book.ports import BookRepository
from library.loan.ports import LoanRepository
from library.loan.repositories import SqlLoanRepository
from library.loan.use_cases.borrow_book import BorrowBookUseCase
from library.loan.use_cases.return_book import ReturnBookUseCase
from library.member.api.dependencies import get_member_repo
from library.member.ports import MemberRepository
from library.shared.api.dependencies import get_clock, get_session
from library.shared.ports import Clock


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
