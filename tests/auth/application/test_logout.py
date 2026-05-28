from library.auth.application import (
    LoginCommand,
    LoginUseCase,
    LogoutCommand,
    LogoutUseCase,
)
from library.auth.domain import RefreshTokenRepository, TokenIssuer
from library.member.domain import Member, MemberRepository
from library.shared.application import Clock, PasswordHasher


async def _login_and_get_token(
    members, tokens, hasher, issuer, clock, valid_member: Member
):
    login_uc = LoginUseCase(
        members=members,
        tokens=tokens,
        hasher=hasher,
        issuer=issuer,
        clock=clock,
        refresh_token_ttl_days=30,
    )
    pair = await login_uc.execute(
        LoginCommand(email=valid_member.email.value, password="password")
    )
    return pair.refresh_token


class TestLogoutUseCase:
    async def test_logout_revokes_refresh_token(
        self,
        member_repo_with_member: MemberRepository,
        refresh_token_repo: RefreshTokenRepository,
        password_hasher: PasswordHasher,
        token_issuer: TokenIssuer,
        clock: Clock,
        valid_member: Member,
    ):
        refresh = await _login_and_get_token(
            member_repo_with_member,
            refresh_token_repo,
            password_hasher,
            token_issuer,
            clock,
            valid_member,
        )
        use_case = LogoutUseCase(
            tokens=refresh_token_repo, issuer=token_issuer, clock=clock
        )

        await use_case.execute(LogoutCommand(refresh_token=refresh))

        stored = await refresh_token_repo.find_by_hash(
            token_issuer.hash_refresh_token(refresh)
        )
        assert stored is not None
        assert stored.is_revoked

    async def test_logout_unknown_token_is_silent(
        self,
        refresh_token_repo: RefreshTokenRepository,
        token_issuer: TokenIssuer,
        clock: Clock,
    ):
        use_case = LogoutUseCase(
            tokens=refresh_token_repo, issuer=token_issuer, clock=clock
        )
        # Should not raise
        await use_case.execute(LogoutCommand(refresh_token="never-existed"))

    async def test_logout_is_idempotent(
        self,
        member_repo_with_member: MemberRepository,
        refresh_token_repo: RefreshTokenRepository,
        password_hasher: PasswordHasher,
        token_issuer: TokenIssuer,
        clock: Clock,
        valid_member: Member,
    ):
        refresh = await _login_and_get_token(
            member_repo_with_member,
            refresh_token_repo,
            password_hasher,
            token_issuer,
            clock,
            valid_member,
        )
        use_case = LogoutUseCase(
            tokens=refresh_token_repo, issuer=token_issuer, clock=clock
        )
        await use_case.execute(LogoutCommand(refresh_token=refresh))
        # Second logout: no-op, no exception
        await use_case.execute(LogoutCommand(refresh_token=refresh))
