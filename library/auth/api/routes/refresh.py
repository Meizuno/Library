from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from library.auth.api.dependencies import get_refresh_tokens_use_case
from library.auth.api.schemas import TokenResponse
from library.auth.use_cases.refresh_tokens import (
    RefreshTokensCommand,
    RefreshTokensUseCase,
)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/refresh")
async def refresh(
    request: RefreshRequest,
    refresh_use_case: RefreshTokensUseCase = Depends(
        get_refresh_tokens_use_case
    ),
) -> TokenResponse:
    pair = await refresh_use_case.execute(
        RefreshTokensCommand(refresh_token=request.refresh_token)
    )
    return TokenResponse.from_pair(pair)
