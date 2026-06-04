from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from library.auth.api.dependencies import get_logout_use_case
from library.auth.use_cases.logout import LogoutCommand, LogoutUseCase


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/logout", status_code=204)
async def logout(
    request: LogoutRequest,
    logout_use_case: LogoutUseCase = Depends(get_logout_use_case),
) -> None:
    await logout_use_case.execute(
        LogoutCommand(refresh_token=request.refresh_token)
    )
