from datetime import timedelta

from library.auth.application.commands import LoginCommand
from library.auth.application.token_pair import TokenPair
from library.auth.domain import (
    CredentialVerifier,
    RefreshToken,
    RefreshTokenRepository,
    TokenIssuer,
)
from library.shared.application import Clock


class LoginUseCase:
    """Authenticates an email+password pair and issues a token pair.

    Credential verification is delegated to the `CredentialVerifier` port,
    whose impl (in member.infrastructure) knows how member credentials are
    actually stored. The auth slice doesn't import MemberRepository or
    PasswordHasher directly — kept the auth.application layer free of
    member-domain leaks.
    """

    def __init__(
        self,
        credentials: CredentialVerifier,
        tokens: RefreshTokenRepository,
        issuer: TokenIssuer,
        clock: Clock,
        refresh_token_ttl_days: int,
    ):
        self._credentials = credentials
        self._tokens = tokens
        self._issuer = issuer
        self._clock = clock
        self._refresh_ttl = timedelta(days=refresh_token_ttl_days)

    async def execute(self, command: LoginCommand) -> TokenPair:
        # Raises InvalidCredentials on failure — the CredentialVerifier
        # impl is responsible for that.
        member_id = await self._credentials.verify(
            command.email, command.password
        )

        access_token = self._issuer.issue_access_token(member_id)
        refresh_raw = self._issuer.generate_refresh_token()
        refresh_record = RefreshToken(
            member_id=member_id,
            token_hash=self._issuer.hash_refresh_token(refresh_raw),
            expires_at=self._clock.now() + self._refresh_ttl,
        )
        await self._tokens.create(refresh_record)

        return TokenPair(access_token=access_token, refresh_token=refresh_raw)
