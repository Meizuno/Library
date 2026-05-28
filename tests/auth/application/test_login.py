import pytest

from library.auth.application import (
    InvalidCredentials,
    LoginCommand,
    LoginUseCase,
)
from library.auth.domain import (
    CredentialVerifier,
    RefreshTokenRepository,
    TokenIssuer,
)
from library.member.domain import Member, MemberRepository
from library.shared.application import Clock


def _make_use_case(
    credentials, tokens, issuer, clock
) -> LoginUseCase:
    return LoginUseCase(
        credentials=credentials,
        tokens=tokens,
        issuer=issuer,
        clock=clock,
        refresh_token_ttl_days=30,
    )


class TestLoginUseCase:
    async def test_login_success_returns_token_pair(
        self,
        # seeds the member that the CredentialVerifier finds
        member_repo_with_member: MemberRepository,
        credential_verifier: CredentialVerifier,
        refresh_token_repo: RefreshTokenRepository,
        token_issuer: TokenIssuer,
        clock: Clock,
        valid_member: Member,
    ):
        use_case = _make_use_case(
            credential_verifier,
            refresh_token_repo,
            token_issuer,
            clock,
        )

        pair = await use_case.execute(
            LoginCommand(email=valid_member.email.value, password="password")
        )

        assert pair.access_token
        assert pair.refresh_token
        # Access token decodes back to the member id
        assert token_issuer.verify_access_token(pair.access_token) == (
            valid_member.id
        )

    async def test_login_persists_hashed_refresh_token(
        self,
        member_repo_with_member: MemberRepository,  # noqa: ARG002
        credential_verifier: CredentialVerifier,
        refresh_token_repo: RefreshTokenRepository,
        token_issuer: TokenIssuer,
        clock: Clock,
        valid_member: Member,
    ):
        use_case = _make_use_case(
            credential_verifier,
            refresh_token_repo,
            token_issuer,
            clock,
        )

        pair = await use_case.execute(
            LoginCommand(email=valid_member.email.value, password="password")
        )

        stored = await refresh_token_repo.find_by_hash(
            token_issuer.hash_refresh_token(pair.refresh_token)
        )
        assert stored is not None
        assert stored.member_id == valid_member.id
        assert not stored.is_revoked

    async def test_login_wrong_password_raises(
        self,
        member_repo_with_member: MemberRepository,  # noqa: ARG002
        credential_verifier: CredentialVerifier,
        refresh_token_repo: RefreshTokenRepository,
        token_issuer: TokenIssuer,
        clock: Clock,
        valid_member: Member,
    ):
        use_case = _make_use_case(
            credential_verifier,
            refresh_token_repo,
            token_issuer,
            clock,
        )

        with pytest.raises(InvalidCredentials):
            await use_case.execute(
                LoginCommand(
                    email=valid_member.email.value, password="wrong"
                )
            )

    async def test_login_unknown_email_raises(
        self,
        credential_verifier: CredentialVerifier,
        refresh_token_repo: RefreshTokenRepository,
        token_issuer: TokenIssuer,
        clock: Clock,
    ):
        use_case = _make_use_case(
            credential_verifier,
            refresh_token_repo,
            token_issuer,
            clock,
        )

        with pytest.raises(InvalidCredentials):
            await use_case.execute(
                LoginCommand(email="nobody@example.com", password="password")
            )

    async def test_login_invalid_email_format_raises(
        self,
        credential_verifier: CredentialVerifier,
        refresh_token_repo: RefreshTokenRepository,
        token_issuer: TokenIssuer,
        clock: Clock,
    ):
        use_case = _make_use_case(
            credential_verifier,
            refresh_token_repo,
            token_issuer,
            clock,
        )

        with pytest.raises(InvalidCredentials):
            await use_case.execute(
                LoginCommand(email="not-an-email", password="password")
            )
