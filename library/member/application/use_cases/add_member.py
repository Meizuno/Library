from library.member.application.commands import AddMemberCommand
from library.member.application.exceptions import MemberAlreadyExists
from library.member.domain import Email, Member, MemberRepository, Password
from library.notification.domain import Notification, Notifier
from library.shared.application import PasswordHasher


_WELCOME_SUBJECT = "Welcome to the library"
_WELCOME_BODY_TEMPLATE = (
    "Hi {name},\n\nYour library account is ready. Happy reading!"
)


class AddMemberUseCase:
    def __init__(
        self,
        member_repo: MemberRepository,
        hasher: PasswordHasher,
        notifier: Notifier,
    ):
        self._member_repo = member_repo
        self._hasher = hasher
        self._notifier = notifier

    async def execute(self, command: AddMemberCommand) -> Member:
        email = Email(command.email)
        password = Password(command.password)
        if await self._member_repo.find_by_email(email):
            raise MemberAlreadyExists(
                f"Member with email {command.email} already exists"
            )

        member = Member(
            name=command.name,
            email=email,
            password_hash=self._hasher.hash(password.value),
        )
        await self._member_repo.create(member)
        await self._notifier.send(
            recipient=member.email.value,
            notification=Notification(
                subject=_WELCOME_SUBJECT,
                body=_WELCOME_BODY_TEMPLATE.format(name=member.name),
            ),
        )
        return member
