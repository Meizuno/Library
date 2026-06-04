from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from library.book.api.dependencies import get_read_book_use_case
from library.book.api.schemas import BookResponse
from library.book.ports import BookAvailability
from library.book.use_cases.read_book import ReadBookUseCase
from library.shared.api.dependencies import get_book_availability

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/{book_id}")
async def read_book(
    book_id: UUID,
    read_book_use_case: ReadBookUseCase = Depends(get_read_book_use_case),
    availability: BookAvailability = Depends(get_book_availability),
) -> BookResponse:
    book = await read_book_use_case.execute(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    return BookResponse.from_domain(
        book, is_available=await availability.is_available(book.id)
    )
