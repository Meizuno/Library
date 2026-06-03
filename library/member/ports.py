from typing import Protocol
from uuid import UUID

from library.member.models import Email, Member


class MemberRepository(Protocol):
    async def create(self, member: Member) -> None: ...
    async def update(self, member: Member) -> None: ...
    async def find_by_id(self, member_id: UUID) -> Member | None: ...
    async def find_by_email(self, email: Email) -> Member | None: ...
    async def list_all(self) -> list[Member]: ...
    async def delete(self, member_id: UUID) -> None: ...


class VerificationTokenIssuer(Protocol):
    """Port for issuing and verifying email-verification tokens.

    Owned by the member module because email verification is a member-feature
    concern. Implementations are free to use any token mechanism (JWT,
    DB-backed single-use, etc.); the default impl
    (`PyJWTVerificationTokenIssuer`) uses a short-lived JWT signed with the
    JWT secret and a `purpose=verify_email` claim.

    Implementations raise `InvalidVerificationToken` (member.exceptions) when
    the token is unrecognized, malformed, or expired.
    """

    def issue(self, member_id: UUID) -> str: ...
    def verify(self, token: str) -> UUID: ...
