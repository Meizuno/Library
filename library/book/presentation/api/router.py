from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from library.book.application import (
    AddBookCommand,
    AddBookUseCase,
    DeleteBookUseCase,
    ListBooksUseCase,
    ReadBookUseCase,
    UpdateBookCommand,
    UpdateBookUseCase,
)
from library.book.domain import BookAvailability
from library.book.presentation.api import dependencies
from library.book.presentation.api.schemas import (
    BookCreate,
    BookResponse,
    BookUpdate,
)
from library.shared.presentation.api.dependencies import get_book_availability


router = APIRouter(prefix="/books", tags=["books"])


@router.get("")
async def list_books(
    search: str | None = None,
    list_books_use_case: ListBooksUseCase = Depends(
        dependencies.get_list_books_use_case
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


@router.post("", status_code=201)
async def create_book(
    command: BookCreate,
    add_book_use_case: AddBookUseCase = Depends(
        dependencies.get_add_book_use_case
    ),
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


@router.get("/{book_id}")
async def read_book(
    book_id: UUID,
    read_book_use_case: ReadBookUseCase = Depends(
        dependencies.get_read_book_use_case
    ),
    availability: BookAvailability = Depends(get_book_availability),
) -> BookResponse:
    book = await read_book_use_case.execute(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    return BookResponse.from_domain(
        book, is_available=await availability.is_available(book.id)
    )


@router.put("/{book_id}")
async def update_book(
    book_id: UUID,
    command: BookUpdate,
    update_book_use_case: UpdateBookUseCase = Depends(
        dependencies.get_update_book_use_case
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


@router.delete("/{book_id}", status_code=204)
async def delete_book(
    book_id: UUID,
    delete_book_use_case: DeleteBookUseCase = Depends(
        dependencies.get_delete_book_use_case
    ),
) -> None:
    await delete_book_use_case.execute(book_id)
