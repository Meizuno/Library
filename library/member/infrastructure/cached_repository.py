import json
from uuid import UUID

from library.member.domain import Email, Member, MemberRepository
from library.shared.infrastructure.cache import Cache


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
