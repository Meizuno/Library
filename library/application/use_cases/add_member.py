from library.domain import Member, Email, MemberRepository
from library.application import AddMemberCommand, MemberAlreadyExists


class AddMemberUseCase:
    def __init__(self, member_repo: MemberRepository):
        self._member_repo = member_repo

    async def execute(self, command: AddMemberCommand) -> Member:
        email = Email(command.email)
        if await self._member_repo.find_by_email(email):
            raise MemberAlreadyExists(
                f"Member with email {command.email} already exists"
            )

        member = Member(name=command.name, email=email)
        await self._member_repo.save(member)
        return member
