from uuid import UUID

from sqlalchemy import func, insert, select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from library.member.domain import Email, Member, MemberNotFound
from library.member.infrastructure.sql_table import members_table


class SqlMemberRepository:
    """SQL-backed repository for Member.

    Implements **soft delete**: `delete()` stamps `members.deleted_at`
    rather than removing the row, and every read filters
    `deleted_at IS NULL` so deleted members are invisible to use cases.
    The physical row stays in place so historical loans can keep
    referencing it (the loans → members FK with ondelete=RESTRICT
    relies on this).
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    def _row_to_member(self, row) -> Member:
        member = Member(
            name=row.name,
            email=Email(row.email),
            password_hash=row.password_hash,
            is_verified=row.is_verified,
        )
        member.id = row.id
        return member

    async def create(self, member: Member) -> None:
        stmt = insert(members_table).values(
            id=member.id,
            name=member.name,
            email=member.email.value,
            password_hash=member.password_hash,
            is_verified=member.is_verified,
        )
        await self._session.execute(stmt)

    async def update(self, member: Member) -> None:
        stmt = (
            sql_update(members_table)
            .where(
                members_table.c.id == member.id,
                members_table.c.deleted_at.is_(None),
            )
            .values(
                name=member.name,
                email=member.email.value,
                password_hash=member.password_hash,
                is_verified=member.is_verified,
            )
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            raise MemberNotFound(f"Member {member.id} not found")

    async def find_by_id(self, member_id: UUID) -> Member | None:
        stmt = select(members_table).where(
            members_table.c.id == member_id,
            members_table.c.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        row = result.first()
        return self._row_to_member(row) if row else None

    async def find_by_email(self, email: Email) -> Member | None:
        stmt = select(members_table).where(
            members_table.c.email == email.value,
            members_table.c.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        row = result.first()
        return self._row_to_member(row) if row else None

    async def list_all(self) -> list[Member]:
        stmt = select(members_table).where(
            members_table.c.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        return [self._row_to_member(row) for row in rows]

    async def delete(self, member_id: UUID) -> None:
        stmt = (
            sql_update(members_table)
            .where(
                members_table.c.id == member_id,
                members_table.c.deleted_at.is_(None),
            )
            # pylint: disable-next=not-callable
            .values(deleted_at=func.now())
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            raise MemberNotFound(f"Member {member_id} not found")
