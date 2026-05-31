from datetime import datetime
from typing import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from library.auth.domain import RefreshToken, RefreshTokenNotFound
from library.auth.infrastructure import SqlRefreshTokenRepository
from library.shared.infrastructure import metadata


@pytest.fixture
async def repo() -> AsyncGenerator[SqlRefreshTokenRepository, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    session = AsyncSession(engine)
    yield SqlRefreshTokenRepository(session)
    await session.close()
    await engine.dispose()


class TestSqlRefreshTokenRepository:
    async def test_update_unknown_token_raises_domain_exception(
        self, repo: SqlRefreshTokenRepository
    ):
        token = RefreshToken(
            member_id=uuid4(),
            token_hash="never-stored",
            expires_at=datetime(2026, 6, 1),
        )
        with pytest.raises(RefreshTokenNotFound):
            await repo.update(token)

    async def test_create_then_update_succeeds(
        self, repo: SqlRefreshTokenRepository
    ):
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

    async def test_find_by_hash_returns_none_when_missing(
        self, repo: SqlRefreshTokenRepository
    ):
        assert await repo.find_by_hash("nope") is None
