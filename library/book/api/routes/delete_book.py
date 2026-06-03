from uuid import UUID

from fastapi import APIRouter, Depends

from library.book.api.dependencies import get_delete_book_use_case
from library.book.use_cases.delete_book import DeleteBookUseCase

router = APIRouter(prefix="/books", tags=["books"])


@router.delete("/{book_id}", status_code=204)
async def delete_book(
    book_id: UUID,
    delete_book_use_case: DeleteBookUseCase = Depends(
        get_delete_book_use_case
    ),
) -> None:
    await delete_book_use_case.execute(book_id)
