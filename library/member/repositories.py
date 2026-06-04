import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    String,
    Table,
    Uuid,
    func,
    insert,
    select,
)
from sqlalchemy import (
    update as sql_update,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import false as sql_false

from library.auth.exceptions import InvalidCredentials
from library.member.exceptions import (
    InvalidVerificationToken,
    MemberNotFound,
)
from library.member.models import Email, Member
from library.member.ports import MemberRepository
from library.shared.adapters import metadata
from library.shared.ports import Cache, PasswordHasher

members_table = Table(
    "members",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("name", String, nullable=False),
    Column("email", String, nullable=False, unique=True),
    Column("password_hash", String, nullable=False),
    # `server_default` ensures pre-existing rows from before this column
    # was added get a sane value; new rows always supply it explicitly.
    Column(
        "is_verified",
        Boolean,
        nullable=False,
        server_default=sql_false(),
    ),
    # Soft-delete marker. NULL = active row. Set to the server's
    # current timestamp on `delete()`; reads filter rows where this
    # is non-NULL so deleted members are invisible to use cases.
    Column("deleted_at", DateTime, nullable=True),
)


class SqlMemberRepository:
    """SQL-backed repository for Member.

    Implements **soft delete**: `delete()` stamps `members.deleted_at`
    rather than removing the row, and every read filters
    `deleted_at IS NULL` so deleted members are invisible to use cases.
    The physical row stays in place so historical loans can keep
    referencing it (the loans → members FK with ondelete=RESTRICT
    relies on this).
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    def _row_to_member(self, row: Any) -> Member:
        member = Member(
            name=row.name,
            email=Email(row.email),
            password_hash=row.password_hash,
            is_verified=row.is_verified,
        )
        member.id = row.id
        return member

    async def create(self, member: Member) -> None:
        stmt = insert(members_table).values(
            id=member.id,
            name=member.name,
            email=member.email.value,
            password_hash=member.password_hash,
            is_verified=member.is_verified,
        )
        await self._session.execute(stmt)

    async def update(self, member: Member) -> None:
        stmt = (
            sql_update(members_table)
            .where(
                members_table.c.id == member.id,
                members_table.c.deleted_at.is_(None),
            )
            .values(
                name=member.name,
                email=member.email.value,
                password_hash=member.password_hash,
                is_verified=member.is_verified,
            )
            .returning(members_table.c.id)
        )
        result = await self._session.execute(stmt)
        if result.scalar_one_or_none() is None:
            raise MemberNotFound(f"Member {member.id} not found")

    async def find_by_id(self, member_id: UUID) -> Member | None:
        stmt = select(members_table).where(
            members_table.c.id == member_id,
            members_table.c.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        row = result.first()
        return self._row_to_member(row) if row else None

    async def find_by_email(self, email: Email) -> Member | None:
        stmt = select(members_table).where(
            members_table.c.email == email.value,
            members_table.c.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        row = result.first()
        return self._row_to_member(row) if row else None

    async def list_all(self) -> list[Member]:
        stmt = select(members_table).where(
            members_table.c.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        return [self._row_to_member(row) for row in rows]

    async def delete(self, member_id: UUID) -> None:
        stmt = (
            sql_update(members_table)
            .where(
                members_table.c.id == member_id,
                members_table.c.deleted_at.is_(None),
            )
            .values(deleted_at=func.now())
            .returning(members_table.c.id)
        )
        result = await self._session.execute(stmt)
        if result.scalar_one_or_none() is None:
            raise MemberNotFound(f"Member {member_id} not found")


class CachedMemberRepository:
    _DATA_PREFIX = "cache:member:id:"

    def __init__(self, inner_repo: MemberRepository, cache: Cache):
        self._inner_repo = inner_repo
        self._cache = cache

    def _data_key(self, member_id: UUID) -> str:
        return f"{self._DATA_PREFIX}{member_id}"

    def _member_to_json(self, member: Member) -> str:
        return json.dumps(
            {
                "id": str(member.id),
                "name": member.name,
                "email": member.email.value,
                "password_hash": member.password_hash,
                "is_verified": member.is_verified,
            }
        )

    def _json_to_member(self, raw: str) -> Member:
        data = json.loads(raw)
        member = Member(
            name=data["name"],
            email=Email(data["email"]),
            password_hash=data["password_hash"],
            is_verified=data.get("is_verified", False),
        )
        member.id = UUID(data["id"])
        return member

    async def create(self, member: Member) -> None:
        await self._inner_repo.create(member)
        await self._cache.delete(self._data_key(member.id))

    async def update(self, member: Member) -> None:
        await self._inner_repo.update(member)
        await self._cache.delete(self._data_key(member.id))

    async def find_by_id(self, member_id: UUID) -> Member | None:
        raw = await self._cache.get(self._data_key(member_id))
        if raw is not None:
            return self._json_to_member(raw)

        member = await self._inner_repo.find_by_id(member_id)
        if member is not None:
            await self._cache.set(
                self._data_key(member_id), self._member_to_json(member)
            )

        return member

    async def find_by_email(self, email: Email) -> Member | None:
        return await self._inner_repo.find_by_email(email)

    async def list_all(self) -> list[Member]:
        return await self._inner_repo.list_all()

    async def delete(self, member_id: UUID) -> None:
        await self._inner_repo.delete(member_id)
        await self._cache.delete(self._data_key(member_id))


class MemberCredentialVerifier:
    """Implements `auth.ports.CredentialVerifier` against the member module.

    Lives in member.repositories because it knows how member credentials
    are stored (password_hash on the Member entity, email as a value object,
    lookup via MemberRepository). The auth module's LoginUseCase consumes
    it via the port; auth.use_cases never imports member.models.
    """

    def __init__(
        self,
        member_repo: MemberRepository,
        hasher: PasswordHasher,
    ):
        self._member_repo = member_repo
        self._hasher = hasher

    async def verify(self, email: str, password: str) -> UUID:
        try:
            email_vo = Email(email)
        except ValueError as exc:
            raise InvalidCredentials(
                "Invalid email or password"
            ) from exc

        member = await self._member_repo.find_by_email(email_vo)
        if member is None or not self._hasher.verify(
            password, member.password_hash
        ):
            raise InvalidCredentials("Invalid email or password")
        return member.id


_VERIFY_EMAIL_PURPOSE = "verify_email"


class PyJWTVerificationTokenIssuer:
    """Concrete `VerificationTokenIssuer` using PyJWT (HS256).

    Signs a `purpose=verify_email` claim alongside `sub`, `iat`, `exp`. The
    purpose check prevents an access token (which carries no purpose claim
    or a different one) from being substituted for a verification token.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        ttl_hours: int = 24,
    ):
        if not secret_key:
            raise ValueError("secret_key cannot be empty")
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._ttl = timedelta(hours=ttl_hours)

    def issue(self, member_id: UUID) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(member_id),
            "purpose": _VERIFY_EMAIL_PURPOSE,
            "iat": int(now.timestamp()),
            "exp": int((now + self._ttl).timestamp()),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def verify(self, token: str) -> UUID:
        try:
            payload = jwt.decode(
                token, self._secret_key, algorithms=[self._algorithm]
            )
        except jwt.PyJWTError as exc:
            raise InvalidVerificationToken(str(exc)) from exc

        if payload.get("purpose") != _VERIFY_EMAIL_PURPOSE:
            raise InvalidVerificationToken(
                f"expected purpose {_VERIFY_EMAIL_PURPOSE!r}, "
                f"got {payload.get('purpose')!r}"
            )

        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise InvalidVerificationToken("token missing sub claim")
        try:
            return UUID(sub)
        except ValueError as exc:
            raise InvalidVerificationToken(
                "sub claim is not a valid UUID"
            ) from exc
