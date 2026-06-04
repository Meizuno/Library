from pydantic import BaseModel

from library.auth.models import TokenPair


class TokenResponse(BaseModel):
    """Response shape shared across /auth/login and /auth/refresh. Per-route
    request shapes (LoginRequest, RefreshRequest, LogoutRequest) live with
    their route in api/routes/*.py.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    @classmethod
    def from_pair(cls, pair: TokenPair) -> "TokenResponse":
        return cls(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
        )
