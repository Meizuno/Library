from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from library.loan.api.dependencies import get_borrow_book_use_case
from library.loan.api.schemas import LoanResponse
from library.loan.use_cases.borrow_book import (
    BorrowBookCommand,
    BorrowBookUseCase,
)


class BorrowBookCreate(BaseModel):
    book_id: UUID
    member_id: UUID


router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("", status_code=201)
async def borrow_book(
    command: BorrowBookCreate,
    borrow_book_use_case: BorrowBookUseCase = Depends(
        get_borrow_book_use_case
    ),
) -> LoanResponse:
    loan = await borrow_book_use_case.execute(
        BorrowBookCommand(
            book_id=command.book_id, member_id=command.member_id
        )
    )
    return LoanResponse.from_domain(loan)
