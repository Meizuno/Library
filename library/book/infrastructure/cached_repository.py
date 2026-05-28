import json
from uuid import UUID

from library.book.domain import Book, ISBN, BookRepository
from library.shared.infrastructure.cache import Cache


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
            }
        )

    def _json_to_book(self, raw: str) -> Book:
        data = json.loads(raw)
        book = Book(
            title=data["title"], author=data["author"], isbn=ISBN(data["isbn"])
        )
        book.id = UUID(data["id"])
        return book

    async def save(self, book: Book) -> None:
        await self._inner_repo.save(book)
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

    async def list_all(self) -> list[Book]:
        return await self._inner_repo.list_all()

    async def delete(self, book_id: UUID) -> None:
        await self._inner_repo.delete(book_id)
        await self._cache.delete(self._data_key(book_id))
