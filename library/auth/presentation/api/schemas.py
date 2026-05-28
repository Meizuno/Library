from pydantic import BaseModel, EmailStr, Field

from library.auth.application import TokenPair


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    @classmethod
    def from_pair(cls, pair: TokenPair) -> "TokenResponse":
        return cls(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
        )


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)
