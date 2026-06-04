from datetime import datetime
from uuid import uuid4

import pytest

from library.auth.exceptions import (
    RefreshTokenExpired,
    RefreshTokenInvalid,
    RefreshTokenRevoked,
)
from library.auth.models import RefreshToken
from library.auth.ports import (
    CredentialVerifier,
    RefreshTokenRepository,
    TokenIssuer,
)
from library.auth.use_cases.login import LoginCommand, LoginUseCase
from library.auth.use_cases.refresh_tokens import (
    RefreshTokensCommand,
    RefreshTokensUseCase,
)
from library.member.models import Member
from library.member.ports import MemberRepository
from library.shared.ports import Clock
from tests.conftest import FakeClock


async def _login(
    credentials, tokens, issuer, clock, valid_member: Member
):
    login_uc = LoginUseCase(
        credentials=credentials,
        tokens=tokens,
        issuer=issuer,
        clock=clock,
        refresh_token_ttl_days=30,
    )
    return await login_uc.execute(
        LoginCommand(email=valid_member.email.value, password="password")
    )


class TestRefreshTokensUseCase:
    async def test_refresh_returns_new_pair(
        self,
        member_repo_with_member: MemberRepository,
        credential_verifier: CredentialVerifier,
        refresh_token_repo: RefreshTokenRepository,
        token_issuer: TokenIssuer,
        clock: Clock,
        valid_member: Member,
    ):
        pair = await _login(
            credential_verifier,
            refresh_token_repo,
            token_issuer,
            clock,
            valid_member,
        )

        use_case = RefreshTokensUseCase(
            tokens=refresh_token_repo,
            issuer=token_issuer,
            clock=clock,
            refresh_token_ttl_days=30,
        )

        new_pair = await use_case.execute(
            RefreshTokensCommand(refresh_token=pair.refresh_token)
        )

        assert new_pair.refresh_token != pair.refresh_token
        # may equal the old one if the FakeClock didn't advance — the
        # access-token string content is opaque, only its validity matters
        assert new_pair.access_token

    async def test_refresh_revokes_old_refresh_token(
        self,
        member_repo_with_member: MemberRepository,
        credential_verifier: CredentialVerifier,
        refresh_token_repo: RefreshTokenRepository,
        token_issuer: TokenIssuer,
        clock: Clock,
        valid_member: Member,
    ):
        pair = await _login(
            credential_verifier,
            refresh_token_repo,
            token_issuer,
            clock,
            valid_member,
        )

        use_case = RefreshTokensUseCase(
            tokens=refresh_token_repo,
            issuer=token_issuer,
            clock=clock,
            refresh_token_ttl_days=30,
        )
        await use_case.execute(
            RefreshTokensCommand(refresh_token=pair.refresh_token)
        )

        # The OLD refresh token must now be rejected
        with pytest.raises(RefreshTokenRevoked):
            await use_case.execute(
                RefreshTokensCommand(refresh_token=pair.refresh_token)
            )

    async def test_refresh_unknown_token_raises(
        self,
        refresh_token_repo: RefreshTokenRepository,
        token_issuer: TokenIssuer,
        clock: Clock,
    ):
        use_case = RefreshTokensUseCase(
            tokens=refresh_token_repo,
            issuer=token_issuer,
            clock=clock,
            refresh_token_ttl_days=30,
        )
        with pytest.raises(RefreshTokenInvalid):
            await use_case.execute(
                RefreshTokensCommand(refresh_token="garbage")
            )

    async def test_refresh_expired_token_raises(
        self,
        refresh_token_repo: RefreshTokenRepository,
        token_issuer: TokenIssuer,
    ):
        raw = token_issuer.generate_refresh_token()
        record = RefreshToken(
            member_id=uuid4(),
            token_hash=token_issuer.hash_refresh_token(raw),
            expires_at=datetime(2026, 5, 1, 0, 0, 0),
        )
        await refresh_token_repo.create(record)

        late_clock = FakeClock(datetime(2026, 6, 1, 0, 0, 0))
        use_case = RefreshTokensUseCase(
            tokens=refresh_token_repo,
            issuer=token_issuer,
            clock=late_clock,
            refresh_token_ttl_days=30,
        )
        with pytest.raises(RefreshTokenExpired):
            await use_case.execute(RefreshTokensCommand(refresh_token=raw))
