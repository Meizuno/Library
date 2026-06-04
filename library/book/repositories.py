import json
from uuid import UUID

from sqlalchemy import (
    Column,
    DateTime,
    String,
    Table,
    Uuid,
    func,
    insert,
    or_,
    select,
    update as sql_update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from library.book.exceptions import BookNotFound
from library.book.models import ISBN, Book
from library.book.ports import BookRepository
from library.shared.adapters import metadata
from library.shared.ports import Cache

books_table = Table(
    "books",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("title", String, nullable=False),
    Column("author", String, nullable=False),
    Column("isbn", String, nullable=False, unique=True),
    Column("description", String, nullable=False, server_default=""),
    # Soft-delete marker. NULL = active row. Set to the server's
    # current timestamp on `delete()`; reads filter rows where this
    # is non-NULL so deleted books are invisible to use cases.
    Column("deleted_at", DateTime, nullable=True),
)


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

    async def list_all(self, search: str | None = None) -> list[Book]:
        stmt = select(books_table).where(books_table.c.deleted_at.is_(None))
        needle = search.strip() if search else ""
        if needle:
            # `icontains(..., autoescape=True)` escapes %/_ in the input
            # so user-supplied wildcards do not leak into the LIKE pattern.
            stmt = stmt.where(
                or_(
                    books_table.c.title.icontains(needle, autoescape=True),
                    books_table.c.author.icontains(needle, autoescape=True),
                )
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


class CachedBookRepository:
    _DATA_PREFIX = "cache:book:id:"

    def __init__(self, inner_repo: BookRepository, cache: Cache):
        self._inner_repo = inner_repo
        self._cache = cache

    def _data_key(self, book_id: UUID) -> str:
        return f"{self._DATA_PREFIX}{book_id}"

    def _book_to_json(self, book: Book) -> str:
        return json.dumps(
            {
                "id": str(book.id),
                "title": book.title,
                "author": book.author,
                "isbn": book.isbn.value,
                "description": book.description,
            }
        )

    def _json_to_book(self, raw: str) -> Book:
        data = json.loads(raw)
        book = Book(
            title=data["title"],
            author=data["author"],
            isbn=ISBN(data["isbn"]),
            description=data.get("description", ""),
        )
        book.id = UUID(data["id"])
        return book

    async def create(self, book: Book) -> None:
        await self._inner_repo.create(book)
        await self._cache.delete(self._data_key(book.id))

    async def update(self, book: Book) -> None:
        await self._inner_repo.update(book)
        await self._cache.delete(self._data_key(book.id))

    async def find_by_id(self, book_id: UUID) -> Book | None:
        raw = await self._cache.get(self._data_key(book_id))
        if raw is not None:
            return self._json_to_book(raw)

        book = await self._inner_repo.find_by_id(book_id)
        if book is not None:
            await self._cache.set(
                self._data_key(book_id), self._book_to_json(book)
            )

        return book

    async def find_by_isbn(self, isbn: ISBN) -> Book | None:
        return await self._inner_repo.find_by_isbn(isbn)

    async def list_all(self, search: str | None = None) -> list[Book]:
        # Lists are not cached (cache invalidation across arbitrary
        # filter combinations would be its own can of worms); pass
        # straight through to the inner repository.
        return await self._inner_repo.list_all(search=search)

    async def delete(self, book_id: UUID) -> None:
        await self._inner_repo.delete(book_id)
        await self._cache.delete(self._data_key(book_id))
