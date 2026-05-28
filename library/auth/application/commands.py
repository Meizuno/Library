from dataclasses import dataclass


@dataclass(frozen=True)
class LoginCommand:
    email: str
    password: str


@dataclass(frozen=True)
class RefreshTokensCommand:
    refresh_token: str


@dataclass(frozen=True)
class LogoutCommand:
    refresh_token: str
