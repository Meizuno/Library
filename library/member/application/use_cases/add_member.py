from library.member.application.commands import AddMemberCommand
from library.member.application.exceptions import MemberAlreadyExists
from library.member.domain import (
    Email,
    Member,
    MemberRepository,
    Password,
    VerificationTokenIssuer,
)
from library.notification.domain import Notification, Notifier
from library.shared.application import PasswordHasher


_WELCOME_SUBJECT = "Welcome to the library"
_WELCOME_BODY_TEMPLATE = (
    "Hi {name},\n\n"
    "Your library account is ready. Verify your email by opening this link\n"
    "(it includes a single-use token; the verify flow accepts the token\n"
    "via POST /members/verify):\n\n"
    "{link}\n\n"
    "The link expires in 24 hours.\n\n"
    "Happy reading!"
)


class AddMemberUseCase:
    def __init__(
        self,
        member_repo: MemberRepository,
        hasher: PasswordHasher,
        notifier: Notifier,
        verification_tokens: VerificationTokenIssuer,
        app_base_url: str,
    ):
        self._member_repo = member_repo
        self._hasher = hasher
        self._notifier = notifier
        self._verification_tokens = verification_tokens
        self._app_base_url = app_base_url.rstrip("/")

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

        token = self._verification_tokens.issue(member.id)
        link = f"{self._app_base_url}/members/verify?token={token}"
        await self._notifier.send(
            recipient=member.email.value,
            notification=Notification(
                subject=_WELCOME_SUBJECT,
                body=_WELCOME_BODY_TEMPLATE.format(
                    name=member.name, link=link
                ),
            ),
        )
        return member
