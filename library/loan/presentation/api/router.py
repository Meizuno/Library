from uuid import UUID

from fastapi import APIRouter, Depends

from library.loan.application import (
    BorrowBookCommand,
    BorrowBookUseCase,
    ReturnBookCommand,
    ReturnBookUseCase,
)
from library.loan.presentation.api import dependencies
from library.loan.presentation.api.schemas import (
    BorrowBookCreate,
    LoanResponse,
)


router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("", status_code=201)
async def borrow_book(
    command: BorrowBookCreate,
    borrow_book_use_case: BorrowBookUseCase = Depends(
        dependencies.get_borrow_book_use_case
    ),
) -> LoanResponse:
    loan = await borrow_book_use_case.execute(
        BorrowBookCommand(
            book_id=command.book_id, member_id=command.member_id
        )
    )
    return LoanResponse.from_domain(loan)


@router.post("/{loan_id}/return")
async def return_book(
    loan_id: UUID,
    return_book_use_case: ReturnBookUseCase = Depends(
        dependencies.get_return_book_use_case
    ),
) -> LoanResponse:
    loan = await return_book_use_case.execute(ReturnBookCommand(loan_id=loan_id))
    return LoanResponse.from_domain(loan)
