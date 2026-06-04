"""SQL-specific tests for soft-delete semantics on SqlMemberRepository.

See tests/book/repositories/test_soft_delete.py for the rationale —
the contract suite verifies observable behavior; these tests verify the
SQL-impl-specific guarantee that delete is *soft* (the row stays present
with `deleted_at` stamped) plus the secondary guarantees that follow
from it.
"""
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from library.member.exceptions import MemberNotFound
from library.member.models import Member
from library.member.repositories import SqlMemberRepository, members_table
from library.shared.adapters import metadata


@pytest.fixture
async def sql_repo_and_session() -> AsyncGenerator[
    tuple[SqlMemberRepository, AsyncSession], None
]:
    """SqlMemberRepository plus a handle on its session, so tests can
    issue raw SELECTs that bypass the repository's `deleted_at IS NULL`
    filter and observe the physical row state."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    session = AsyncSession(engine)
    yield SqlMemberRepository(session), session
    await session.close()
    await engine.dispose()


class TestSoftDeleteMember:
    async def test_delete_keeps_row_physically_present_with_deleted_at(
        self,
        sql_repo_and_session,
        valid_member: Member,
    ):
        repo, session = sql_repo_and_session
        await repo.create(valid_member)

        await repo.delete(valid_member.id)

        # Direct SELECT bypassing the repo's filter — proves the row
        # is still in the table.
        row = (
            await session.execute(
                select(members_table).where(
                    members_table.c.id == valid_member.id
                )
            )
        ).first()
        assert row is not None
        assert row.deleted_at is not None

    async def test_delete_then_find_by_email_returns_none(
        self,
        sql_repo_and_session,
        valid_member: Member,
    ):
        repo, _ = sql_repo_and_session
        await repo.create(valid_member)
        await repo.delete(valid_member.id)

        assert await repo.find_by_email(valid_member.email) is None

    async def test_update_on_soft_deleted_member_raises(
        self,
        sql_repo_and_session,
        valid_member: Member,
    ):
        repo, _ = sql_repo_and_session
        await repo.create(valid_member)
        await repo.delete(valid_member.id)

        valid_member.name = "Different name"
        with pytest.raises(MemberNotFound):
            await repo.update(valid_member)

    async def test_double_delete_raises(
        self,
        sql_repo_and_session,
        valid_member: Member,
    ):
        repo, _ = sql_repo_and_session
        await repo.create(valid_member)
        await repo.delete(valid_member.id)

        with pytest.raises(MemberNotFound):
            await repo.delete(valid_member.id)
