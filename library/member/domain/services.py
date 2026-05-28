from typing import Protocol
from uuid import UUID


class VerificationTokenIssuer(Protocol):
    """Port for issuing and verifying email-verification tokens.

    Owned by the member slice because email verification is a member-feature
    concern. Implementations are free to use any token mechanism (JWT,
    DB-backed single-use, etc.); the default impl
    (`PyJWTVerificationTokenIssuer`) uses a short-lived JWT signed with the
    JWT secret and a `purpose=verify_email` claim.

    Implementations raise `InvalidVerificationToken` (member.domain) when
    the token is unrecognized, malformed, or expired.
    """

    def issue(self, member_id: UUID) -> str: ...
    def verify(self, token: str) -> UUID: ...
