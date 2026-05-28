from library.auth.application.commands import LogoutCommand
from library.auth.domain import RefreshTokenRepository, TokenIssuer
from library.shared.application import Clock


class LogoutUseCase:
    """Idempotent. If the refresh token is unknown or already revoked,
    the operation succeeds silently (don't leak information about token validity)."""

    def __init__(
        self,
        tokens: RefreshTokenRepository,
        issuer: TokenIssuer,
        clock: Clock,
    ):
        self._tokens = tokens
        self._issuer = issuer
        self._clock = clock

    async def execute(self, command: LogoutCommand) -> None:
        presented_hash = self._issuer.hash_refresh_token(command.refresh_token)
        record = await self._tokens.find_by_hash(presented_hash)
        if record is None or record.is_revoked:
            return
        record.revoke(self._clock.now())
        await self._tokens.update(record)
