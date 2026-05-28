from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    cache_ttl: int = 300
    log_level: str = "INFO"
    log_format: Literal["console", "json"] = "console"
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="forbid")
