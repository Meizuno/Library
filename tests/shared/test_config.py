import pytest
from pydantic import ValidationError

from library.shared.config import Settings


_VALID_SECRET = "x" * 32  # exactly the HS256 minimum

_VALID_KWARGS: dict = {
    "database_url": "sqlite+aiosqlite:///:memory:",
    "redis_url": "redis://localhost:6379/0",
    "jwt_secret_key": _VALID_SECRET,
}


def _settings(**overrides) -> Settings:
    """Build Settings from explicit kwargs (bypassing env). The
    `_env_file=None` arg disables .env loading so a stray local file
    can't pollute these tests."""
    return Settings(_env_file=None, **{**_VALID_KWARGS, **overrides})


class TestSettingsHappyPath:
    def test_minimum_valid_config(self):
        s = _settings()
        assert s.database_url == "sqlite+aiosqlite:///:memory:"
        assert s.redis_url == "redis://localhost:6379/0"
        assert s.jwt_secret_key == _VALID_SECRET

    def test_defaults_applied(self):
        s = _settings()
        assert s.cache_ttl == 300
        assert s.log_level == "INFO"
        assert s.log_format == "console"
        assert s.jwt_algorithm == "HS256"
        assert s.access_token_ttl_minutes == 15
        assert s.refresh_token_ttl_days == 30
        # SMTP defaults: no host (dev-mode console logging), no TLS, no auth.
        assert s.smtp_host is None
        assert s.smtp_port == 587
        assert s.smtp_use_tls is False
        assert s.smtp_username is None
        assert s.smtp_password is None

    def test_smtp_use_tls_can_be_enabled(self):
        s = _settings(smtp_use_tls=True)
        assert s.smtp_use_tls is True

    def test_postgres_url_accepted(self):
        _settings(database_url="postgresql+asyncpg://u:p@host:5432/db")
        _settings(database_url="postgresql://u:p@host:5432/db")

    def test_secure_redis_url_accepted(self):
        _settings(redis_url="rediss://host:6379/0")


class TestSettingsFailFast:
    @pytest.mark.parametrize(
        "missing",
        ["database_url", "redis_url", "jwt_secret_key"],
    )
    def test_missing_required_field_raises(
        self, missing: str, monkeypatch
    ):
        # The conftest pre-populates these env vars for runtime tests; clear
        # them here so pydantic-settings can't fall back to them.
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        kwargs = dict(_VALID_KWARGS)
        del kwargs[missing]
        with pytest.raises(ValidationError):
            Settings(_env_file=None, **kwargs)

    @pytest.mark.parametrize(
        "url",
        [
            "",
            "not-a-url",
            "mysql://u:p@host/db",
            "http://example.com",
        ],
    )
    def test_invalid_database_url_prefix_raises(self, url: str):
        with pytest.raises(ValidationError, match="database_url"):
            _settings(database_url=url)

    @pytest.mark.parametrize(
        "url",
        [
            "",
            "http://localhost:6379",
            "memcached://localhost",
        ],
    )
    def test_invalid_redis_url_prefix_raises(self, url: str):
        with pytest.raises(ValidationError, match="redis_url"):
            _settings(redis_url=url)

    @pytest.mark.parametrize("ttl", [0, -1, -100])
    def test_non_positive_cache_ttl_raises(self, ttl: int):
        with pytest.raises(ValidationError):
            _settings(cache_ttl=ttl)

    @pytest.mark.parametrize("ttl", [0, -1])
    def test_non_positive_access_token_ttl_raises(self, ttl: int):
        with pytest.raises(ValidationError):
            _settings(access_token_ttl_minutes=ttl)

    @pytest.mark.parametrize("ttl", [0, -1])
    def test_non_positive_refresh_token_ttl_raises(self, ttl: int):
        with pytest.raises(ValidationError):
            _settings(refresh_token_ttl_days=ttl)

    @pytest.mark.parametrize(
        "secret",
        ["", "short", "x" * 31],  # below 32-byte HS256 minimum
    )
    def test_short_jwt_secret_raises(self, secret: str):
        with pytest.raises(ValidationError):
            _settings(jwt_secret_key=secret)

    @pytest.mark.parametrize(
        "level",
        ["info", "verbose", "TRACE", "", "WARN"],
    )
    def test_invalid_log_level_raises(self, level: str):
        with pytest.raises(ValidationError):
            _settings(log_level=level)

    @pytest.mark.parametrize("fmt", ["plain", "xml", "JSON"])
    def test_invalid_log_format_raises(self, fmt: str):
        with pytest.raises(ValidationError):
            _settings(log_format=fmt)

    @pytest.mark.parametrize(
        "algo",
        ["HS128", "none", "MD5", ""],
    )
    def test_invalid_jwt_algorithm_raises(self, algo: str):
        with pytest.raises(ValidationError):
            _settings(jwt_algorithm=algo)

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            _settings(unknown_field="oops")
