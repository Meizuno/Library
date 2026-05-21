from uuid import UUID

from library.domain import MemberRepository


class DeleteMemberUseCase:
    def __init__(self, member_repo: MemberRepository):
        self._member_repo = member_repo

    async def execute(self, member_id: UUID) -> None:
        await self._member_repo.delete(member_id)
