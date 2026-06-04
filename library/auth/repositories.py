import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    Uuid,
    insert,
    select,
    update as sql_update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from library.auth.exceptions import InvalidAccessToken, RefreshTokenNotFound
from library.auth.models import RefreshToken
from library.shared.adapters import metadata

refresh_tokens_table = Table(
    "refresh_tokens",
    metadata,
    Column("id", Uuid, primary_key=True),
    # FK with ondelete="RESTRICT" mirrors loans.member_id: in normal app
    # flow nothing ever fires it (members are soft-deleted, their row
    # stays), but it forbids any raw-SQL or future hard-delete path
    # that would otherwise leave orphan refresh-token rows behind.
    Column(
        "member_id",
        Uuid,
        ForeignKey("members.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("token_hash", String, nullable=False, unique=True),
    Column("expires_at", DateTime, nullable=False),
    Column("revoked_at", DateTime, nullable=True),
    Index("ix_refresh_tokens_member_id", "member_id"),
)


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


class PyJWTTokenIssuer:
    """Concrete `TokenIssuer` for the auth module: issues + verifies access
    tokens (stateless JWTs) and generates + hashes refresh tokens (opaque
    random strings hashed with SHA-256 before storage).

    Verification tokens (e.g. for email confirmation) live in the member
    module's `PyJWTVerificationTokenIssuer` — this issuer is purely an
    auth concern.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_ttl_minutes: int = 15,
    ):
        if not secret_key:
            raise ValueError("secret_key cannot be empty")
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_ttl = timedelta(minutes=access_token_ttl_minutes)

    def issue_access_token(self, member_id: UUID) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(member_id),
            "iat": int(now.timestamp()),
            "exp": int((now + self._access_ttl).timestamp()),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def verify_access_token(self, token: str) -> UUID:
        try:
            payload = jwt.decode(
                token, self._secret_key, algorithms=[self._algorithm]
            )
        except jwt.PyJWTError as exc:
            raise InvalidAccessToken(str(exc)) from exc

        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise InvalidAccessToken("token missing sub claim")
        try:
            return UUID(sub)
        except ValueError as exc:
            raise InvalidAccessToken("sub claim is not a valid UUID") from exc

    def generate_refresh_token(self) -> str:
        return secrets.token_urlsafe(64)

    def hash_refresh_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
