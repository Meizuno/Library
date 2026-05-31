from uuid import UUID

from sqlalchemy import func, insert, select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from library.book.domain import Book, ISBN, BookNotFound
from library.book.infrastructure.sql_table import books_table


class SqlBookRepository:
    """SQL-backed repository for Book.

    Implements **soft delete**: `delete()` stamps `books.deleted_at` rather
    than removing the row, and every read filters `deleted_at IS NULL` so
    deleted books are invisible to use cases. The physical row stays in
    place so historical loans can keep referencing it (the loans → books
    FK with ondelete=RESTRICT relies on this).
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    def _row_to_book(self, row) -> Book:
        book = Book(
            title=row.title,
            author=row.author,
            isbn=ISBN(row.isbn),
            description=row.description,
        )
        book.id = row.id
        return book

    async def create(self, book: Book) -> None:
        stmt = insert(books_table).values(
            id=book.id,
            title=book.title,
            author=book.author,
            isbn=book.isbn.value,
            description=book.description,
        )
        await self._session.execute(stmt)

    async def update(self, book: Book) -> None:
        stmt = (
            sql_update(books_table)
            .where(
                books_table.c.id == book.id,
                books_table.c.deleted_at.is_(None),
            )
            .values(
                title=book.title,
                author=book.author,
                isbn=book.isbn.value,
                description=book.description,
            )
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            raise BookNotFound(f"Book {book.id} not found")

    async def find_by_id(self, book_id: UUID) -> Book | None:
        stmt = select(books_table).where(
            books_table.c.id == book_id,
            books_table.c.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        row = result.first()
        return self._row_to_book(row) if row else None

    async def find_by_isbn(self, isbn: ISBN) -> Book | None:
        stmt = select(books_table).where(
            books_table.c.isbn == isbn.value,
            books_table.c.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        row = result.first()
        return self._row_to_book(row) if row else None

    async def list_all(self) -> list[Book]:
        stmt = select(books_table).where(
            books_table.c.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        return [self._row_to_book(row) for row in rows]

    async def delete(self, book_id: UUID) -> None:
        stmt = (
            sql_update(books_table)
            .where(
                books_table.c.id == book_id,
                books_table.c.deleted_at.is_(None),
            )
            # pylint: disable-next=not-callable
            .values(deleted_at=func.now())
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            raise BookNotFound(f"Book {book_id} not found")
