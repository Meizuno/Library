from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from library.auth.application import (
    LoginUseCase,
    LogoutUseCase,
    RefreshTokensUseCase,
)
from library.auth.domain import RefreshTokenRepository, TokenIssuer
from library.auth.infrastructure import (
    PyJWTTokenIssuer,
    SqlRefreshTokenRepository,
)
from library.member.domain import MemberRepository
from library.member.presentation.api.dependencies import get_member_repo
from library.shared.application import Clock, PasswordHasher
from library.shared.config import Settings
from library.shared.presentation.api.dependencies import (
    get_clock,
    get_password_hasher,
    get_session,
    get_settings,
)


def get_refresh_token_repo(
    session: AsyncSession = Depends(get_session),
) -> RefreshTokenRepository:
    return SqlRefreshTokenRepository(session)


def get_token_issuer(
    settings: Settings = Depends(get_settings),
) -> TokenIssuer:
    return PyJWTTokenIssuer(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_ttl_minutes=settings.access_token_ttl_minutes,
    )


def get_login_use_case(
    members: MemberRepository = Depends(get_member_repo),
    tokens: RefreshTokenRepository = Depends(get_refresh_token_repo),
    hasher: PasswordHasher = Depends(get_password_hasher),
    issuer: TokenIssuer = Depends(get_token_issuer),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> LoginUseCase:
    return LoginUseCase(
        members=members,
        tokens=tokens,
        hasher=hasher,
        issuer=issuer,
        clock=clock,
        refresh_token_ttl_days=settings.refresh_token_ttl_days,
    )


def get_refresh_tokens_use_case(
    tokens: RefreshTokenRepository = Depends(get_refresh_token_repo),
    issuer: TokenIssuer = Depends(get_token_issuer),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> RefreshTokensUseCase:
    return RefreshTokensUseCase(
        tokens=tokens,
        issuer=issuer,
        clock=clock,
        refresh_token_ttl_days=settings.refresh_token_ttl_days,
    )


def get_logout_use_case(
    tokens: RefreshTokenRepository = Depends(get_refresh_token_repo),
    issuer: TokenIssuer = Depends(get_token_issuer),
    clock: Clock = Depends(get_clock),
) -> LogoutUseCase:
    return LogoutUseCase(tokens=tokens, issuer=issuer, clock=clock)
