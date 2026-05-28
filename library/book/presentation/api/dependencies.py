from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from library.book.application import (
    AddBookUseCase,
    DeleteBookUseCase,
    ListBooksUseCase,
    ReadBookUseCase,
    UpdateBookUseCase,
)
from library.book.domain import BookRepository
from library.book.infrastructure import CachedBookRepository, SqlBookRepository
from library.shared.infrastructure.cache import Cache
from library.shared.presentation.api.dependencies import get_cache, get_session


def get_book_repo(
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
) -> BookRepository:
    return CachedBookRepository(SqlBookRepository(session), cache)


def get_add_book_use_case(
    book_repo: BookRepository = Depends(get_book_repo),
) -> AddBookUseCase:
    return AddBookUseCase(book_repo)


def get_read_book_use_case(
    book_repo: BookRepository = Depends(get_book_repo),
) -> ReadBookUseCase:
    return ReadBookUseCase(book_repo)


def get_list_books_use_case(
    book_repo: BookRepository = Depends(get_book_repo),
) -> ListBooksUseCase:
    return ListBooksUseCase(book_repo)


def get_delete_book_use_case(
    book_repo: BookRepository = Depends(get_book_repo),
) -> DeleteBookUseCase:
    return DeleteBookUseCase(book_repo)


def get_update_book_use_case(
    book_repo: BookRepository = Depends(get_book_repo),
) -> UpdateBookUseCase:
    return UpdateBookUseCase(book_repo)
