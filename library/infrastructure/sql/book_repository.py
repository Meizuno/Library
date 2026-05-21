from uuid import UUID

from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from library.domain import Book, ISBN, BookNotFound
from library.infrastructure.sql.tables import books_table


class SqlBookRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    def _row_to_book(self, row) -> Book:
        book = Book(
            title=row.title,
            author=row.author,
            isbn=ISBN(row.isbn),
        )
        book.id = row.id
        return book

    async def save(self, book: Book) -> None:
        stmt = select(books_table.c.id).where(books_table.c.id == book.id)
        existing = await self._session.execute(stmt)
        if existing.scalar_one_or_none() is not None:
            stmt = (
                update(books_table)
                .where(books_table.c.id == book.id)
                .values(
                    title=book.title,
                    author=book.author,
                    isbn=book.isbn.value,
                )
            )
        else:
            stmt = insert(books_table).values(
                id=book.id,
                title=book.title,
                author=book.author,
                isbn=book.isbn.value,
            )

        await self._session.execute(stmt)

    async def find_by_id(self, book_id: UUID) -> Book | None:
        stmt = select(books_table).where(books_table.c.id == book_id)
        result = await self._session.execute(stmt)
        row = result.first()
        return self._row_to_book(row) if row else None

    async def find_by_isbn(self, isbn: ISBN) -> Book | None:
        stmt = select(books_table).where(books_table.c.isbn == isbn.value)
        result = await self._session.execute(stmt)
        row = result.first()
        return self._row_to_book(row) if row else None

    async def list_all(self) -> list[Book]:
        stmt = select(books_table)
        result = await self._session.execute(stmt)
        rows = result.all()
        return [self._row_to_book(row) for row in rows]

    async def delete(self, book_id: UUID) -> None:
        stmt = delete(books_table).where(books_table.c.id == book_id)
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            raise BookNotFound(f"Book {book_id} not found")
