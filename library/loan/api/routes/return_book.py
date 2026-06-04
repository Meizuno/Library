from uuid import UUID

from fastapi import APIRouter, Depends

from library.loan.api.dependencies import get_return_book_use_case
from library.loan.api.schemas import LoanResponse
from library.loan.use_cases.return_book import (
    ReturnBookCommand,
    ReturnBookUseCase,
)

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("/{loan_id}/return")
async def return_book(
    loan_id: UUID,
    return_book_use_case: ReturnBookUseCase = Depends(
        get_return_book_use_case
    ),
) -> LoanResponse:
    loan = await return_book_use_case.execute(
        ReturnBookCommand(loan_id=loan_id)
    )
    return LoanResponse.from_domain(loan)
