from library.member.domain import Member, MemberRepository


class ListMembersUseCase:
    def __init__(self, member_repo: MemberRepository):
        self._member_repo = member_repo

    async def execute(self) -> list[Member]:
        return await self._member_repo.list_all()
