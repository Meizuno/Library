from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from library.book.application import (
    AddBookCommand,
    AddBookUseCase,
    DeleteBookUseCase,
    ListBooksUseCase,
    ReadBookUseCase,
)
from library.book.presentation.api import dependencies
from library.book.presentation.api.schemas import BookCreate, BookResponse


router = APIRouter(prefix="/books", tags=["books"])


@router.get("")
async def list_books(
    list_books_use_case: ListBooksUseCase = Depends(
        dependencies.get_list_books_use_case
    ),
) -> list[BookResponse]:
    books = await list_books_use_case.execute()
    return [BookResponse.from_domain(book) for book in books]


@router.post("", status_code=201)
async def create_book(
    command: BookCreate,
    add_book_use_case: AddBookUseCase = Depends(
        dependencies.get_add_book_use_case
    ),
) -> BookResponse:
    book = await add_book_use_case.execute(
        AddBookCommand(
            title=command.title, author=command.author, isbn=command.isbn
        )
    )
    return BookResponse.from_domain(book)


@router.get("/{book_id}")
async def read_book(
    book_id: UUID,
    read_book_use_case: ReadBookUseCase = Depends(
        dependencies.get_read_book_use_case
    ),
) -> BookResponse:
    book = await read_book_use_case.execute(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    return BookResponse.from_domain(book)


@router.delete("/{book_id}", status_code=204)
async def delete_book(
    book_id: UUID,
    delete_book_use_case: DeleteBookUseCase = Depends(
        dependencies.get_delete_book_use_case
    ),
) -> None:
    await delete_book_use_case.execute(book_id)
