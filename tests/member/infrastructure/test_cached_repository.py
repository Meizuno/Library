from uuid import uuid4
from unittest.mock import AsyncMock

from library.member.domain import Email, Member, MemberRepository
from library.member.infrastructure import CachedMemberRepository
from library.shared.infrastructure.cache import InMemoryCache


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
