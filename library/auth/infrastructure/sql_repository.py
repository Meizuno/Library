from uuid import UUID

from sqlalchemy import insert, select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from library.auth.domain import RefreshToken, RefreshTokenNotFound
from library.auth.infrastructure.sql_table import refresh_tokens_table


class SqlRefreshTokenRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    def _row_to_token(self, row) -> RefreshToken:
        token = RefreshToken(
            member_id=row.member_id,
            token_hash=row.token_hash,
            expires_at=row.expires_at,
            revoked_at=row.revoked_at,
        )
        token.id = row.id
        return token

    async def create(self, token: RefreshToken) -> None:
        stmt = insert(refresh_tokens_table).values(
            id=token.id,
            member_id=token.member_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
        )
        await self._session.execute(stmt)

    async def update(self, token: RefreshToken) -> None:
        stmt = (
            sql_update(refresh_tokens_table)
            .where(refresh_tokens_table.c.id == token.id)
            .values(
                member_id=token.member_id,
                token_hash=token.token_hash,
                expires_at=token.expires_at,
                revoked_at=token.revoked_at,
            )
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            raise RefreshTokenNotFound(f"RefreshToken {token.id} not found")

    async def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(refresh_tokens_table).where(
            refresh_tokens_table.c.token_hash == token_hash
        )
        result = await self._session.execute(stmt)
        row = result.first()
        return self._row_to_token(row) if row else None

    async def find_by_id(self, token_id: UUID) -> RefreshToken | None:
        stmt = select(refresh_tokens_table).where(
            refresh_tokens_table.c.id == token_id
        )
        result = await self._session.execute(stmt)
        row = result.first()
        return self._row_to_token(row) if row else None
