from uuid import UUID

from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from library.member.domain import Email, Member, MemberNotFound
from library.member.infrastructure.sql_table import members_table


class SqlMemberRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    def _row_to_member(self, row) -> Member:
        member = Member(
            name=row.name,
            email=Email(row.email),
        )
        member.id = row.id
        return member

    async def save(self, member: Member) -> None:
        stmt = select(members_table.c.id).where(members_table.c.id == member.id)
        existing = await self._session.execute(stmt)
        if existing.scalar_one_or_none() is not None:
            stmt = (
                update(members_table)
                .where(members_table.c.id == member.id)
                .values(
                    name=member.name,
                    email=member.email.value,
                )
            )
        else:
            stmt = insert(members_table).values(
                id=member.id,
                name=member.name,
                email=member.email.value,
            )

        await self._session.execute(stmt)

    async def find_by_id(self, member_id: UUID) -> Member | None:
        stmt = select(members_table).where(members_table.c.id == member_id)
        result = await self._session.execute(stmt)
        row = result.first()
        return self._row_to_member(row) if row else None

    async def find_by_email(self, email: Email) -> Member | None:
        stmt = select(members_table).where(members_table.c.email == email.value)
        result = await self._session.execute(stmt)
        row = result.first()
        return self._row_to_member(row) if row else None

    async def list_all(self) -> list[Member]:
        stmt = select(members_table)
        result = await self._session.execute(stmt)
        rows = result.all()
        return [self._row_to_member(row) for row in rows]

    async def delete(self, member_id: UUID) -> None:
        stmt = delete(members_table).where(members_table.c.id == member_id)
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            raise MemberNotFound(f"member {member_id} not found")
