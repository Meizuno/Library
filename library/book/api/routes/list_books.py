from fastapi import APIRouter, Depends

from library.book.api.dependencies import get_list_books_use_case
from library.book.api.schemas import BookResponse
from library.book.ports import BookAvailability
from library.book.use_cases.list_books import ListBooksUseCase
from library.shared.api.dependencies import get_book_availability

router = APIRouter(prefix="/books", tags=["books"])


@router.get("")
async def list_books(
    search: str | None = None,
    list_books_use_case: ListBooksUseCase = Depends(
        get_list_books_use_case
    ),
    availability: BookAvailability = Depends(get_book_availability),
) -> list[BookResponse]:
    books = await list_books_use_case.execute(search=search)
    # N+1: one availability check per book. Acceptable at current
    # scale; graduate to a batched port method if list size grows.
    return [
        BookResponse.from_domain(
            book, is_available=await availability.is_available(book.id)
        )
        for book in books
    ]
