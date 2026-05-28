from uuid import UUID

from library.member.domain import Member, MemberRepository


class ReadMemberUseCase:
    def __init__(self, member_repo: MemberRepository):
        self._member_repo = member_repo

    async def execute(self, member_id: UUID) -> Member | None:
        return await self._member_repo.find_by_id(member_id)
