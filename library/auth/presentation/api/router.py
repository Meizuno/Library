from fastapi import APIRouter, Depends

from library.auth.application import (
    LoginCommand,
    LoginUseCase,
    LogoutCommand,
    LogoutUseCase,
    RefreshTokensCommand,
    RefreshTokensUseCase,
)
from library.auth.presentation.api import dependencies
from library.auth.presentation.api.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    request: LoginRequest,
    login_use_case: LoginUseCase = Depends(dependencies.get_login_use_case),
) -> TokenResponse:
    pair = await login_use_case.execute(
        LoginCommand(email=request.email, password=request.password)
    )
    return TokenResponse.from_pair(pair)


@router.post("/refresh")
async def refresh(
    request: RefreshRequest,
    refresh_use_case: RefreshTokensUseCase = Depends(
        dependencies.get_refresh_tokens_use_case
    ),
) -> TokenResponse:
    pair = await refresh_use_case.execute(
        RefreshTokensCommand(refresh_token=request.refresh_token)
    )
    return TokenResponse.from_pair(pair)


@router.post("/logout", status_code=204)
async def logout(
    request: LogoutRequest,
    logout_use_case: LogoutUseCase = Depends(dependencies.get_logout_use_case),
) -> None:
    await logout_use_case.execute(
        LogoutCommand(refresh_token=request.refresh_token)
    )
