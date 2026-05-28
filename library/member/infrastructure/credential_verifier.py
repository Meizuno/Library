from uuid import UUID

from library.auth.application import InvalidCredentials
from library.member.domain import Email, MemberRepository
from library.shared.application import PasswordHasher


class MemberCredentialVerifier:
    """Implements `auth.domain.CredentialVerifier` against the member slice.

    Lives in member.infrastructure because it knows how member credentials
    are stored (password_hash on the Member entity, email as a value object,
    lookup via MemberRepository). The auth slice's LoginUseCase consumes
    it via the port; auth.application no longer depends on member.domain
    at the application layer.
    """

    def __init__(
        self,
        member_repo: MemberRepository,
        hasher: PasswordHasher,
    ):
        self._member_repo = member_repo
        self._hasher = hasher

    async def verify(self, email: str, password: str) -> UUID:
        try:
            email_vo = Email(email)
        except ValueError as exc:
            raise InvalidCredentials(
                "Invalid email or password"
            ) from exc

        member = await self._member_repo.find_by_email(email_vo)
        if member is None or not self._hasher.verify(
            password, member.password_hash
        ):
            raise InvalidCredentials("Invalid email or password")
        return member.id
