from typing import Protocol
from uuid import UUID


class TokenIssuer(Protocol):
    """Port for issuing and verifying *authentication* tokens.

    Access tokens are short-lived stateless JWTs (encoded member_id + exp).
    Refresh tokens are opaque random strings; only their hash is stored.

    Verification tokens (e.g. for email confirmation) are NOT this port's
    concern — they live in the feature that owns the verification flow
    (see `library.member.domain.services.VerificationTokenIssuer`).
    """

    def issue_access_token(self, member_id: UUID) -> str: ...
    def verify_access_token(self, token: str) -> UUID: ...
    def generate_refresh_token(self) -> str: ...
    def hash_refresh_token(self, token: str) -> str: ...


class CredentialVerifier(Protocol):
    """Port for verifying an email + password and returning the matching
    member's id.

    Lets the auth slice's LoginUseCase verify credentials without importing
    `MemberRepository`/`PasswordHasher` directly — the impl lives in the
    member slice's infrastructure (see
    `library.member.infrastructure.credential_verifier.MemberCredentialVerifier`).
    Impls raise `InvalidCredentials` (auth.application.exceptions) on
    unknown email, malformed email, or wrong password.
    """

    async def verify(self, email: str, password: str) -> UUID: ...
