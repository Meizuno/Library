from dataclasses import dataclass

from library.member.events import MemberRegistered
from library.member.exceptions import MemberAlreadyExists
from library.member.models import Email, Member, Password
from library.member.ports import MemberRepository
from library.shared.ports import EventPublisher, PasswordHasher


@dataclass(frozen=True)
class AddMemberCommand:
    name: str
    email: str
    password: str


class AddMemberUseCase:
    """Register a new member and emit a MemberRegistered event.

    The use case knows nothing about email, verification tokens, or
    notification channels — that's the whole point of the event bus.
    Subscribers (see library.notification.subscribers) react to the
    event and produce their own side effects. A handler failure does
    not roll back the registration: the InProcessEventBus catches and
    logs.
    """

    def __init__(
        self,
        member_repo: MemberRepository,
        hasher: PasswordHasher,
        event_publisher: EventPublisher,
    ):
        self._member_repo = member_repo
        self._hasher = hasher
        self._event_publisher = event_publisher

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

        await self._event_publisher.publish(
            MemberRegistered(
                member_id=member.id,
                name=member.name,
                email=member.email.value,
            )
        )
        return member
