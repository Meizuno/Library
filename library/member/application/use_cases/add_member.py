from library.member.application.commands import AddMemberCommand
from library.member.application.exceptions import MemberAlreadyExists
from library.member.domain import Email, Member, MemberRepository
from library.shared.application import PasswordHasher


MIN_PASSWORD_LENGTH = 8


class AddMemberUseCase:
    def __init__(
        self, member_repo: MemberRepository, hasher: PasswordHasher
    ):
        self._member_repo = member_repo
        self._hasher = hasher

    async def execute(self, command: AddMemberCommand) -> Member:
        email = Email(command.email)
        if len(command.password) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"password must be at least {MIN_PASSWORD_LENGTH} characters"
            )
        if await self._member_repo.find_by_email(email):
            raise MemberAlreadyExists(
                f"Member with email {command.email} already exists"
            )

        member = Member(
            name=command.name,
            email=email,
            password_hash=self._hasher.hash(command.password),
        )
        await self._member_repo.create(member)
        return member
