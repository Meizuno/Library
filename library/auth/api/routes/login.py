from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field

from library.auth.api.dependencies import get_login_use_case
from library.auth.api.schemas import TokenResponse
from library.auth.use_cases.login import LoginCommand, LoginUseCase


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    request: LoginRequest,
    login_use_case: LoginUseCase = Depends(get_login_use_case),
) -> TokenResponse:
    pair = await login_use_case.execute(
        LoginCommand(email=request.email, password=request.password)
    )
    return TokenResponse.from_pair(pair)
