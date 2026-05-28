from uuid import UUID

from library.member.domain import Email, Member, MemberNotFound


class InMemoryMemberRepository:
    def __init__(self):
        self._member_db: dict[UUID, Member] = {}

    async def save(self, member: Member) -> None:
        self._member_db[member.id] = member

    async def find_by_id(self, member_id: UUID) -> Member | None:
        return self._member_db.get(member_id)

    async def find_by_email(self, email: Email) -> Member | None:
        for member in self._member_db.values():
            if member.email == email:
                return member
        return None

    async def list_all(self) -> list[Member]:
        return list(self._member_db.values())

    async def delete(self, member_id: UUID) -> None:
        if member_id not in self._member_db:
            raise MemberNotFound(f"Member {member_id} not found")

        del self._member_db[member_id]
