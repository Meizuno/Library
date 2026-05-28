from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from library.auth.application import (
    LoginUseCase,
    LogoutUseCase,
    RefreshTokensUseCase,
)
from library.auth.domain import (
    CredentialVerifier,
    RefreshTokenRepository,
    TokenIssuer,
)
from library.auth.infrastructure import SqlRefreshTokenRepository
from library.shared.application import Clock
from library.shared.config import Settings
from library.shared.presentation.api.dependencies import (
    get_clock,
    get_credential_verifier,
    get_session,
    get_settings,
    get_token_issuer,
)


def get_refresh_token_repo(
    session: AsyncSession = Depends(get_session),
) -> RefreshTokenRepository:
    return SqlRefreshTokenRepository(session)


def get_login_use_case(
    credentials: CredentialVerifier = Depends(get_credential_verifier),
    tokens: RefreshTokenRepository = Depends(get_refresh_token_repo),
    issuer: TokenIssuer = Depends(get_token_issuer),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> LoginUseCase:
    return LoginUseCase(
        credentials=credentials,
        tokens=tokens,
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
