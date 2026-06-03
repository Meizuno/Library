from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from library.book.api.dependencies import get_update_book_use_case
from library.book.api.schemas import BookResponse
from library.book.ports import BookAvailability
from library.book.use_cases.update_book import (
    UpdateBookCommand,
    UpdateBookUseCase,
)
from library.shared.presentation.api.dependencies import get_book_availability


class BookUpdate(BaseModel):
    title: str
    author: str
    description: str


router = APIRouter(prefix="/books", tags=["books"])


@router.put("/{book_id}")
async def update_book(
    book_id: UUID,
    command: BookUpdate,
    update_book_use_case: UpdateBookUseCase = Depends(
        get_update_book_use_case
    ),
    availability: BookAvailability = Depends(get_book_availability),
) -> BookResponse:
    book = await update_book_use_case.execute(
        UpdateBookCommand(
            book_id=book_id,
            title=command.title,
            author=command.author,
            description=command.description,
        )
    )
    return BookResponse.from_domain(
        book, is_available=await availability.is_available(book.id)
    )
