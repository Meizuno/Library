from datetime import datetime
from uuid import uuid4

import pytest

from library.auth.domain import RefreshToken, RefreshTokenNotFound
from library.auth.infrastructure import InMemoryRefreshTokenRepository


class TestInMemoryRefreshTokenRepository:
    async def test_update_unknown_token_raises_domain_exception(self):
        repo = InMemoryRefreshTokenRepository()
        token = RefreshToken(
            member_id=uuid4(),
            token_hash="never-stored",
            expires_at=datetime(2026, 6, 1),
        )
        with pytest.raises(RefreshTokenNotFound):
            await repo.update(token)

    async def test_create_then_update_succeeds(self):
        repo = InMemoryRefreshTokenRepository()
        token = RefreshToken(
            member_id=uuid4(),
            token_hash="a-hash",
            expires_at=datetime(2026, 6, 1),
        )
        await repo.create(token)

        token.revoke(datetime(2026, 5, 20))
        await repo.update(token)

        found = await repo.find_by_id(token.id)
        assert found is not None
        assert found.is_revoked

    async def test_find_by_hash_returns_none_when_missing(self):
        repo = InMemoryRefreshTokenRepository()
        assert await repo.find_by_hash("nope") is None
