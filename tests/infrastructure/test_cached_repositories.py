from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from library.domain import (
    Book,
    Member,
    ISBN,
    Email,
    BookRepository,
    MemberRepository,
)
from library.infrastructure import (
    CachedBookRepository,
    CachedMemberRepository,
    InMemoryCache,
)


class TestCachedBookRepository:
    async def test_find_by_id_caches_on_first_call(self, valid_book: Book):
        inner = AsyncMock(spec=BookRepository)
        inner.find_by_id.return_value = valid_book
        repo = CachedBookRepository(inner, InMemoryCache(100))

        first = await repo.find_by_id(valid_book.id)
        second = await repo.find_by_id(valid_book.id)

        assert first == valid_book
        assert second == valid_book
        assert inner.find_by_id.call_count == 1

    async def test_find_by_id_missing_is_not_cached(self):
        inner = AsyncMock(spec=BookRepository)
        inner.find_by_id.return_value = None
        repo = CachedBookRepository(inner, InMemoryCache(100))

        missing_id = uuid4()
        await repo.find_by_id(missing_id)
        await repo.find_by_id(missing_id)

        assert inner.find_by_id.call_count == 2

    async def test_save_invalidates_cache(self, valid_book: Book):
        inner = AsyncMock(spec=BookRepository)
        inner.find_by_id.return_value = valid_book
        repo = CachedBookRepository(inner, InMemoryCache(100))

        await repo.find_by_id(valid_book.id)
        await repo.save(valid_book)
        await repo.find_by_id(valid_book.id)

        assert inner.find_by_id.call_count == 2
        assert inner.save.call_count == 1

    async def test_delete_invalidates_cache(self, valid_book: Book):
        inner = AsyncMock(spec=BookRepository)
        inner.find_by_id.return_value = valid_book
        repo = CachedBookRepository(inner, InMemoryCache(100))

        await repo.find_by_id(valid_book.id)
        await repo.delete(valid_book.id)

        inner.find_by_id.return_value = None
        result = await repo.find_by_id(valid_book.id)

        assert result is None
        assert inner.find_by_id.call_count == 2
        assert inner.delete.call_count == 1

    async def test_find_by_isbn_is_passthrough(
        self, valid_book: Book, valid_isbn: ISBN
    ):
        inner = AsyncMock(spec=BookRepository)
        inner.find_by_isbn.return_value = valid_book
        repo = CachedBookRepository(inner, InMemoryCache(100))

        await repo.find_by_isbn(valid_isbn)
        await repo.find_by_isbn(valid_isbn)

        assert inner.find_by_isbn.call_count == 2

    async def test_list_all_is_passthrough(self):
        inner = AsyncMock(spec=BookRepository)
        inner.list_all.return_value = []
        repo = CachedBookRepository(inner, InMemoryCache(100))

        await repo.list_all()
        await repo.list_all()

        assert inner.list_all.call_count == 2


class TestCachedMemberRepository:
    async def test_find_by_id_caches_on_first_call(self, valid_member: Member):
        inner = AsyncMock(spec=MemberRepository)
        inner.find_by_id.return_value = valid_member
        repo = CachedMemberRepository(inner, InMemoryCache(100))

        first = await repo.find_by_id(valid_member.id)
        second = await repo.find_by_id(valid_member.id)

        assert first == valid_member
        assert second == valid_member
        assert inner.find_by_id.call_count == 1

    async def test_find_by_id_missing_is_not_cached(self):
        inner = AsyncMock(spec=MemberRepository)
        inner.find_by_id.return_value = None
        repo = CachedMemberRepository(inner, InMemoryCache(100))

        missing_id = uuid4()
        await repo.find_by_id(missing_id)
        await repo.find_by_id(missing_id)

        assert inner.find_by_id.call_count == 2

    async def test_save_invalidates_cache(self, valid_member: Member):
        inner = AsyncMock(spec=MemberRepository)
        inner.find_by_id.return_value = valid_member
        repo = CachedMemberRepository(inner, InMemoryCache(100))

        await repo.find_by_id(valid_member.id)
        await repo.save(valid_member)
        await repo.find_by_id(valid_member.id)

        assert inner.find_by_id.call_count == 2
        assert inner.save.call_count == 1

    async def test_delete_invalidates_cache(self, valid_member: Member):
        inner = AsyncMock(spec=MemberRepository)
        inner.find_by_id.return_value = valid_member
        repo = CachedMemberRepository(inner, InMemoryCache(100))

        await repo.find_by_id(valid_member.id)
        await repo.delete(valid_member.id)

        inner.find_by_id.return_value = None
        result = await repo.find_by_id(valid_member.id)

        assert result is None
        assert inner.find_by_id.call_count == 2
        assert inner.delete.call_count == 1

    async def test_find_by_email_is_passthrough(
        self, valid_member: Member, valid_email: Email
    ):
        inner = AsyncMock(spec=MemberRepository)
        inner.find_by_email.return_value = valid_member
        repo = CachedMemberRepository(inner, InMemoryCache(100))

        await repo.find_by_email(valid_email)
        await repo.find_by_email(valid_email)

        assert inner.find_by_email.call_count == 2

    async def test_list_all_is_passthrough(self):
        inner = AsyncMock(spec=MemberRepository)
        inner.list_all.return_value = []
        repo = CachedMemberRepository(inner, InMemoryCache(100))

        await repo.list_all()
        await repo.list_all()

        assert inner.list_all.call_count == 2
