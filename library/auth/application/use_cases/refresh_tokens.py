from datetime import timedelta

from library.auth.application.commands import RefreshTokensCommand
from library.auth.application.token_pair import TokenPair
from library.auth.domain import (
    RefreshToken,
    RefreshTokenExpired,
    RefreshTokenInvalid,
    RefreshTokenRepository,
    RefreshTokenRevoked,
    TokenIssuer,
)
from library.shared.application import Clock


class RefreshTokensUseCase:
    """Rotates the refresh token: revokes the presented one and issues a
    fresh pair (access + refresh). The new refresh token replaces the old
    in the client's possession. Presenting an already-revoked refresh
    token raises RefreshTokenRevoked.
    """

    def __init__(
        self,
        tokens: RefreshTokenRepository,
        issuer: TokenIssuer,
        clock: Clock,
        refresh_token_ttl_days: int,
    ):
        self._tokens = tokens
        self._issuer = issuer
        self._clock = clock
        self._refresh_ttl = timedelta(days=refresh_token_ttl_days)

    async def execute(self, command: RefreshTokensCommand) -> TokenPair:
        presented_hash = self._issuer.hash_refresh_token(command.refresh_token)
        record = await self._tokens.find_by_hash(presented_hash)
        if record is None:
            raise RefreshTokenInvalid("refresh token not recognized")

        now = self._clock.now()
        if record.is_revoked:
            raise RefreshTokenRevoked("refresh token has been revoked")
        if record.is_expired(now):
            raise RefreshTokenExpired("refresh token has expired")

        record.revoke(now)
        await self._tokens.update(record)

        new_raw = self._issuer.generate_refresh_token()
        new_record = RefreshToken(
            member_id=record.member_id,
            token_hash=self._issuer.hash_refresh_token(new_raw),
            expires_at=now + self._refresh_ttl,
        )
        await self._tokens.create(new_record)

        access_token = self._issuer.issue_access_token(record.member_id)
        return TokenPair(access_token=access_token, refresh_token=new_raw)
