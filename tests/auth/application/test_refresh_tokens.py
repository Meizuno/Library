from datetime import datetime
from uuid import uuid4

import pytest

from library.auth.application import (
    LoginCommand,
    LoginUseCase,
    RefreshTokensCommand,
    RefreshTokensUseCase,
)
from library.auth.domain import (
    CredentialVerifier,
    RefreshToken,
    RefreshTokenExpired,
    RefreshTokenInvalid,
    RefreshTokenRepository,
    RefreshTokenRevoked,
    TokenIssuer,
)
from library.member.domain import Member, MemberRepository
from library.shared.application import Clock
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
        member_repo_with_member: MemberRepository,  # noqa: ARG002 — seeds member
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
        assert new_pair.access_token  # may equal old if clock didn't advance — content is opaque

    async def test_refresh_revokes_old_refresh_token(
        self,
        member_repo_with_member: MemberRepository,  # noqa: ARG002
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
