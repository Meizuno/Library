from pydantic import BaseModel

from library.auth.models import TokenPair


class TokenResponse(BaseModel):
    """Response shape shared across /auth/login and /auth/refresh. Per-route
    request shapes (LoginRequest, RefreshRequest, LogoutRequest) live with
    their route in api/routes/*.py.
    """

    access_token: str
    refresh_token: str
    # "bearer" is the OAuth2 token_type identifier per RFC 6750 §3, not a
    # secret — ruff's S105 (hardcoded-password) here is a false positive.
    token_type: str = "bearer"  # noqa: S105

    @classmethod
    def from_pair(cls, pair: TokenPair) -> "TokenResponse":
        return cls(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
        )
