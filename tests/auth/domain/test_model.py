from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from library.auth.domain import RefreshToken


class TestRefreshToken:
    def test_empty_hash_raises(self):
        with pytest.raises(ValueError, match="token_hash cannot be empty"):
            RefreshToken(
                member_id=uuid4(),
                token_hash="",
                expires_at=datetime(2026, 6, 1),
            )

    def test_new_token_is_not_revoked(self):
        token = RefreshToken(
            member_id=uuid4(),
            token_hash="x",
            expires_at=datetime(2026, 6, 1),
        )
        assert token.is_revoked is False

    def test_revoke_sets_revoked_at(self):
        token = RefreshToken(
            member_id=uuid4(),
            token_hash="x",
            expires_at=datetime(2026, 6, 1),
        )
        now = datetime(2026, 5, 20)
        token.revoke(now)
        assert token.is_revoked
        assert token.revoked_at == now

    def test_revoke_is_idempotent(self):
        token = RefreshToken(
            member_id=uuid4(),
            token_hash="x",
            expires_at=datetime(2026, 6, 1),
        )
        first = datetime(2026, 5, 20)
        second = datetime(2026, 5, 21)
        token.revoke(first)
        token.revoke(second)
        assert token.revoked_at == first

    def test_is_expired_when_now_at_or_past_expires(self):
        expires = datetime(2026, 6, 1)
        token = RefreshToken(
            member_id=uuid4(), token_hash="x", expires_at=expires
        )
        assert token.is_expired(expires) is True
        assert token.is_expired(expires + timedelta(seconds=1)) is True
        assert token.is_expired(expires - timedelta(seconds=1)) is False
