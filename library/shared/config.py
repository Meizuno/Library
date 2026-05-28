from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Allow-lists for prefix validation. Used by `database_url` and `redis_url`.
# SQLAlchemy + asyncpg/aiosqlite for the DB; redis-py for the cache.
_ALLOWED_DB_PREFIXES = (
    "postgresql+asyncpg://",
    "postgresql://",
    "sqlite+aiosqlite://",
    "sqlite://",
)
_ALLOWED_REDIS_PREFIXES = ("redis://", "rediss://", "unix://")


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogFormat = Literal["console", "json"]
JwtAlgorithm = Literal["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]


class Settings(BaseSettings):
    """Application configuration. Fail-fast: every constraint is enforced at
    instantiation time (which happens at app startup via `get_settings`),
    so a misconfigured deploy crashes before serving the first request
    rather than failing on the Nth user action."""

    database_url: str
    redis_url: str
    cache_ttl: int = Field(default=300, gt=0, description="seconds")
    log_level: LogLevel = "INFO"
    log_format: LogFormat = "console"
    # HS256 requires >= 32-byte (256-bit) keys. For ASCII secrets, char count
    # equals byte count, so min_length=32 is the right threshold.
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: JwtAlgorithm = "HS256"
    access_token_ttl_minutes: int = Field(default=15, gt=0)
    refresh_token_ttl_days: int = Field(default=30, gt=0)

    # Email / SMTP. When `smtp_host` is None (typical dev), the EmailNotifier
    # logs the email instead of sending — no SMTP server required to run locally.
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, gt=0)
    smtp_from: str = "library@example.com"
    smtp_username: str | None = None
    smtp_password: str | None = None
    # STARTTLS is independent of auth: TLS-only relays exist; so do
    # authenticated-but-plaintext local relays. Caller chooses explicitly.
    smtp_use_tls: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="forbid")

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, v: str) -> str:
        if not any(v.startswith(p) for p in _ALLOWED_DB_PREFIXES):
            raise ValueError(
                "database_url must start with one of "
                f"{_ALLOWED_DB_PREFIXES}"
            )
        return v

    @field_validator("redis_url")
    @classmethod
    def _validate_redis_url(cls, v: str) -> str:
        if not any(v.startswith(p) for p in _ALLOWED_REDIS_PREFIXES):
            raise ValueError(
                "redis_url must start with one of "
                f"{_ALLOWED_REDIS_PREFIXES}"
            )
        return v
