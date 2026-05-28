from uuid import uuid4

import pytest
from fakeredis import FakeAsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from library.member.domain import (
    Email,
    Member,
    MemberNotFound,
    MemberRepository,
)
from library.member.infrastructure import (
    CachedMemberRepository,
    InMemoryMemberRepository,
    SqlMemberRepository,
)
from library.shared.infrastructure.cache import RedisCache


class TestProtocolSatisfaction:
    def test_in_memory_member_repo_satisfies_protocol(self):
        repo: MemberRepository = InMemoryMemberRepository()
        assert hasattr(repo, "create")
        assert hasattr(repo, "update")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_by_email")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")

    def test_cached_member_repo_satisfies_protocol(self, sql_member_repo):
        repo: MemberRepository = CachedMemberRepository(
            sql_member_repo, RedisCache(FakeAsyncRedis(), 300)
        )
        assert hasattr(repo, "create")
        assert hasattr(repo, "update")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_by_email")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")

    def test_sql_member_repo_satisfies_protocol(self):
        repo: MemberRepository = SqlMemberRepository(AsyncSession())
        assert hasattr(repo, "create")
        assert hasattr(repo, "update")
        assert hasattr(repo, "find_by_id")
        assert hasattr(repo, "find_by_email")
        assert hasattr(repo, "list_all")
        assert hasattr(repo, "delete")


class TestMemberRepository:
    async def test_get_list_without_member(
        self, empty_member_repo: MemberRepository
    ):
        assert await empty_member_repo.list_all() == []

    async def test_create_member(
        self, empty_member_repo: MemberRepository, valid_member: Member
    ):
        await empty_member_repo.create(valid_member)
        assert (
            await empty_member_repo.find_by_id(valid_member.id) == valid_member
        )

    async def test_read_unsaved_member(
        self, empty_member_repo: MemberRepository
    ):
        assert await empty_member_repo.find_by_id(uuid4()) is None

    async def test_read_member_by_email(
        self,
        member_repo_with_member: MemberRepository,
        valid_member: Member,
        valid_email: Email,
    ):
        assert (
            await member_repo_with_member.find_by_email(valid_email)
            == valid_member
        )

    async def test_get_list_saved_member(
        self,
        member_repo_with_member: MemberRepository,
        valid_member: Member,
    ):
        assert await member_repo_with_member.list_all() == [valid_member]

    async def test_get_immutable_list_saved_member(
        self,
        member_repo_with_member: MemberRepository,
        valid_member: Member,
    ):
        member_list = await member_repo_with_member.list_all()
        member_list.append(valid_member)
        assert await member_repo_with_member.list_all() == [valid_member]

    async def test_update_saved_member(
        self,
        member_repo_with_member: MemberRepository,
        valid_member: Member,
    ):
        valid_member.name = "Updated name"
        await member_repo_with_member.update(valid_member)
        saved_member = await member_repo_with_member.find_by_id(valid_member.id)
        assert saved_member.name == "Updated name"

    async def test_is_verified_round_trips(
        self,
        empty_member_repo: MemberRepository,
        valid_member: Member,
    ):
        # Default false on create.
        await empty_member_repo.create(valid_member)
        saved = await empty_member_repo.find_by_id(valid_member.id)
        assert saved.is_verified is False

        # Update flips it; persisted value comes back true.
        valid_member.mark_verified()
        await empty_member_repo.update(valid_member)
        saved = await empty_member_repo.find_by_id(valid_member.id)
        assert saved.is_verified is True

    async def test_update_unsaved_member_raises(
        self, empty_member_repo: MemberRepository, valid_member: Member
    ):
        with pytest.raises(MemberNotFound):
            await empty_member_repo.update(valid_member)

    async def test_delete_saved_member(
        self,
        member_repo_with_member: MemberRepository,
        valid_member: Member,
    ):
        assert await member_repo_with_member.delete(valid_member.id) is None
        assert await member_repo_with_member.list_all() == []

    async def test_delete_unsaved_member(
        self, empty_member_repo: MemberRepository
    ):
        with pytest.raises(MemberNotFound):
            await empty_member_repo.delete(uuid4())
