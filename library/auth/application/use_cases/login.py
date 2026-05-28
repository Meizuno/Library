from datetime import timedelta

from library.auth.application.commands import LoginCommand
from library.auth.application.exceptions import InvalidCredentials
from library.auth.application.token_pair import TokenPair
from library.auth.domain import (
    RefreshToken,
    RefreshTokenRepository,
    TokenIssuer,
)
from library.member.domain import Email, MemberRepository
from library.shared.application import Clock, PasswordHasher


class LoginUseCase:
    def __init__(
        self,
        members: MemberRepository,
        tokens: RefreshTokenRepository,
        hasher: PasswordHasher,
        issuer: TokenIssuer,
        clock: Clock,
        refresh_token_ttl_days: int,
    ):
        self._members = members
        self._tokens = tokens
        self._hasher = hasher
        self._issuer = issuer
        self._clock = clock
        self._refresh_ttl = timedelta(days=refresh_token_ttl_days)

    async def execute(self, command: LoginCommand) -> TokenPair:
        try:
            email = Email(command.email)
        except ValueError as exc:
            raise InvalidCredentials("Invalid email or password") from exc

        member = await self._members.find_by_email(email)
        if member is None or not self._hasher.verify(
            command.password, member.password_hash
        ):
            raise InvalidCredentials("Invalid email or password")

        access_token = self._issuer.issue_access_token(member.id)
        refresh_raw = self._issuer.generate_refresh_token()
        refresh_record = RefreshToken(
            member_id=member.id,
            token_hash=self._issuer.hash_refresh_token(refresh_raw),
            expires_at=self._clock.now() + self._refresh_ttl,
        )
        await self._tokens.create(refresh_record)

        return TokenPair(access_token=access_token, refresh_token=refresh_raw)
