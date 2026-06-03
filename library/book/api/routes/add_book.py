from fastapi import APIRouter, Depends
from pydantic import BaseModel

from library.book.api.dependencies import get_add_book_use_case
from library.book.api.schemas import BookResponse
from library.book.use_cases.add_book import AddBookCommand, AddBookUseCase


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str
    description: str = ""


router = APIRouter(prefix="/books", tags=["books"])


@router.post("", status_code=201)
async def create_book(
    command: BookCreate,
    add_book_use_case: AddBookUseCase = Depends(get_add_book_use_case),
) -> BookResponse:
    book = await add_book_use_case.execute(
        AddBookCommand(
            title=command.title,
            author=command.author,
            isbn=command.isbn,
            description=command.description,
        )
    )
    # A freshly-created book has no loans by definition — skip the
    # query, save a round-trip.
    return BookResponse.from_domain(book, is_available=True)
